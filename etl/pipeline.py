#!/usr/bin/env python3
"""
pipeline.py — SEC Investment Adviser Monitor ETL pipeline.

Usage:
  python pipeline.py                   # download latest, auto-detect period
  python pipeline.py --period 202603   # March 2026 (yyyyMM format)
  python pipeline.py --dry-run         # download + parse but don't write to DB

The pipeline:
  1. Scrapes the SEC IAPD page for the registered + exempt Excel URLs
  2. Downloads the files (cached; skips if already on disk)
  3. Parses both files into normalised DataFrames
  4. Loads (upserts) snapshots into PostgreSQL
  5. Computes field-level changes vs. the previous period
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the repo root (one level up from etl/) or current directory
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()

import psycopg2

from downloader import (
    SEC_PAGE_URL,
    date_str_to_period,
    download_file,
    get_latest_urls,
    get_urls_for_period,
)
from differ import compute_changes, get_previous_period
from loader import load_snapshot, period_already_ingested
from parser import parse_xlsx

DATA_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def _get_db_conn() -> "psycopg2.connection":
    """
    Create a psycopg2 connection from DATABASE_URL or individual POSTGRES_*
    env vars.
    """
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)

    host = os.environ.get("POSTGRES_HOST", "db")
    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    dbname = os.environ.get("POSTGRES_DB", "adviser_db")
    user = os.environ.get("POSTGRES_USER", "adviser_user")
    password = os.environ.get("POSTGRES_PASSWORD", "adviser_pass")
    return psycopg2.connect(
        host=host, port=port, dbname=dbname, user=user, password=password
    )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def _yyyymm_to_db_period(period_yyyymm: str) -> str:
    """Convert yyyyMM (e.g. '202603') to DB period YYYY-MM (e.g. '2026-03')."""
    import re as _re
    m = _re.match(r"^(\d{4})(\d{2})$", period_yyyymm)
    if not m:
        raise ValueError(
            f"--period must be in yyyyMM format (e.g. 202603 for March 2026), "
            f"got: {period_yyyymm!r}"
        )
    yyyy, mm = m.group(1), m.group(2)
    if not (1 <= int(mm) <= 12):
        raise ValueError(f"Invalid month '{mm}' in period {period_yyyymm!r}")
    return f"{yyyy}-{mm}"


def _run_local(period_yyyymm: str | None, dry_run: bool) -> None:
    """
    Load every CSV / XLSX file already in DATA_DIR into the database,
    skipping the download step entirely.

    Period is detected from each filename (SEC MMDDYY encoding).
    Use --period YYYYMM to override when filenames don't follow that pattern.

    Registration type defaults to 'SEC'; files whose name contains 'exempt'
    (case-insensitive) are treated as 'Exempt'.
    """
    from collections import defaultdict

    import pandas as pd

    _log("=== SEC Investment Adviser Monitor — ETL Pipeline (local mode) ===")

    # Collect all data files (case-insensitive suffix match)
    exts = {".csv", ".xlsx"}
    files = sorted(p for p in DATA_DIR.iterdir() if p.suffix.lower() in exts)

    if not files:
        _log(f"No CSV or XLSX files found in {DATA_DIR}")
        sys.exit(1)

    _log(f"Found {len(files)} file(s) in {DATA_DIR}")

    # Resolve period override
    period_override: str | None = None
    if period_yyyymm:
        try:
            period_override = _yyyymm_to_db_period(period_yyyymm)
        except ValueError as exc:
            _log(f"ERROR: {exc}")
            sys.exit(1)

    # Group files by period: {period_str: [(path, reg_type), ...]}
    groups: dict[str, list[tuple[Path, str]]] = defaultdict(list)
    skipped = 0

    for f in files:
        if period_override:
            period = period_override
        else:
            period = date_str_to_period(f.name)
            if not period:
                _log(
                    f"  [skip] Cannot detect period from filename: {f.name} "
                    "(use --period YYYYMM to override)"
                )
                skipped += 1
                continue

        name_lower = f.name.lower()
        reg_type = "Exempt" if "exempt" in name_lower and "nonexempt" not in name_lower else "SEC"
        groups[period].append((f, reg_type))

    if skipped:
        _log(f"  Skipped {skipped} file(s) — period could not be detected from filename.")

    if not groups:
        _log("No files could be processed. Provide --period YYYYMM to override detection.")
        sys.exit(1)

    # Database connection
    if not dry_run:
        try:
            conn = _get_db_conn()
        except Exception as exc:
            _log(f"ERROR connecting to database: {exc}")
            sys.exit(1)
    else:
        conn = None  # type: ignore[assignment]

    for period, file_list in sorted(groups.items()):
        _log(f"\n--- Period {period} ({len(file_list)} file(s)) ---")

        if not dry_run and period_already_ingested(period, conn):
            _log(f"  Period {period} already ingested — skipping.")
            continue

        dfs = []
        for path, reg_type in file_list:
            _log(f"  Parsing {path.name} ({reg_type}) …")
            try:
                df = parse_xlsx(path, registration_type=reg_type)
                dfs.append(df)
            except Exception as exc:
                _log(f"  ERROR parsing {path.name}: {exc}")

        if not dfs:
            _log(f"  No data parsed for period {period} — skipping.")
            continue

        df_all = pd.concat(dfs, ignore_index=True)
        df_all = df_all.drop_duplicates(subset=["crd"], keep="last")
        _log(f"  Total rows after merge + dedup: {len(df_all):,}")

        if dry_run:
            _log(f"  Dry-run — sample:\n{df_all[['crd', 'firm_name', 'aum', 'employees']].head(5)}")
            continue

        try:
            count = load_snapshot(df_all, period, conn)
            _log(f"  {count:,} rows loaded.")
        except Exception as exc:
            _log(f"  ERROR loading data: {exc}")
            conn.rollback()
            continue

        try:
            prev_period = get_previous_period(period, conn)
            if prev_period:
                n_changes = compute_changes(prev_period, period, conn)
                _log(f"  {n_changes:,} changes detected ({prev_period} → {period})")
            else:
                _log("  No previous period in DB — skipping diff.")
        except Exception as exc:
            _log(f"  ERROR computing changes: {exc}")
            conn.rollback()

    if conn:
        conn.close()
    _log("=== Local pipeline complete ===")


def run(period_yyyymm: str | None = None, dry_run: bool = False, local: bool = False) -> None:
    if local:
        _run_local(period_yyyymm, dry_run)
        return

    _log("=== SEC Investment Adviser Monitor — ETL Pipeline ===")

    # ------------------------------------------------------------------ #
    # Step 1 — Discover file URLs
    # ------------------------------------------------------------------ #
    _log("Step 1: Fetching file URLs from SEC IAPD page …")
    try:
        if period_yyyymm:
            urls = get_urls_for_period(period_yyyymm, SEC_PAGE_URL)
        else:
            urls = get_latest_urls(SEC_PAGE_URL)
    except Exception as exc:
        _log(f"ERROR fetching SEC page: {exc}")
        sys.exit(1)

    _log(f"  Registered: {urls['registered']}")
    _log(f"  Exempt:     {urls['exempt']}")

    # ------------------------------------------------------------------ #
    # Step 2 — Determine period (YYYY-MM for DB)
    # ------------------------------------------------------------------ #
    if period_yyyymm:
        try:
            period = _yyyymm_to_db_period(period_yyyymm)
        except ValueError as exc:
            _log(f"ERROR: {exc}")
            sys.exit(1)
        _log(f"Step 2: Using specified period: {period}")
    else:
        reg_filename = urls["registered"].split("/")[-1]
        period = date_str_to_period(reg_filename)
        if not period:
            _log(f"ERROR: Could not extract period from filename: {reg_filename}")
            sys.exit(1)
        _log(f"Step 2: Auto-detected period: {period}")

    # ------------------------------------------------------------------ #
    # Step 3 — Check if already ingested (skip if so, unless dry-run)
    # ------------------------------------------------------------------ #
    if not dry_run:
        try:
            conn = _get_db_conn()
        except Exception as exc:
            _log(f"ERROR connecting to database: {exc}")
            sys.exit(1)

        if period_already_ingested(period, conn):
            _log(
                f"Step 3: Period {period} already ingested — skipping. "
                "Use --period with a different value to re-run."
            )
            conn.close()
            return
        _log("Step 3: Period not yet ingested — proceeding.")
    else:
        conn = None  # type: ignore[assignment]
        _log("Step 3: Dry-run mode — skipping DB check.")

    # ------------------------------------------------------------------ #
    # Step 4 — Download files
    # ------------------------------------------------------------------ #
    _log("Step 4: Downloading data files …")
    try:
        reg_path = download_file(urls["registered"], DATA_DIR)
        ex_path = download_file(urls["exempt"], DATA_DIR)
    except Exception as exc:
        _log(f"ERROR downloading files: {exc}")
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Step 5 — Parse
    # ------------------------------------------------------------------ #
    _log("Step 5: Parsing data files …")
    try:
        df_reg = parse_xlsx(reg_path, registration_type="SEC")
        df_ex = parse_xlsx(ex_path, registration_type="Exempt")
    except Exception as exc:
        _log(f"ERROR parsing files: {exc}")
        sys.exit(1)

    import pandas as pd
    df_all = pd.concat([df_reg, df_ex], ignore_index=True)
    # De-duplicate by CRD, keeping the last occurrence
    df_all = df_all.drop_duplicates(subset=["crd"], keep="last")
    _log(
        f"  Total rows after merge + dedup: {len(df_all):,} "
        f"({len(df_reg):,} registered + {len(df_ex):,} exempt)"
    )

    if dry_run:
        _log("Dry-run complete — no data written to database.")
        _log(f"  Sample:\n{df_all[['crd', 'firm_name', 'aum', 'employees']].head(5)}")
        return

    # ------------------------------------------------------------------ #
    # Step 6 — Load into database
    # ------------------------------------------------------------------ #
    _log("Step 6: Loading snapshots into database …")
    try:
        count = load_snapshot(df_all, period, conn)
        _log(f"  {count:,} rows loaded for period {period}")
    except Exception as exc:
        _log(f"ERROR loading data: {exc}")
        conn.rollback()
        conn.close()
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # Step 7 — Compute changes vs. previous period
    # ------------------------------------------------------------------ #
    _log("Step 7: Computing changes vs. previous period …")
    try:
        prev_period = get_previous_period(period, conn)
        if prev_period:
            n_changes = compute_changes(prev_period, period, conn)
            _log(f"  {n_changes:,} changes detected ({prev_period} → {period})")
        else:
            _log("  No previous period found — skipping diff.")
    except Exception as exc:
        _log(f"ERROR computing changes: {exc}")
        conn.rollback()

    conn.close()
    _log("=== Pipeline complete ===")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="SEC Investment Adviser Monitor ETL pipeline",
    )
    parser.add_argument(
        "--period",
        metavar="YYYY-MM",
        help="Override the period (e.g. 2026-03). Auto-detected from filename if omitted.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Download and parse files but do not write to the database.",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help=(
            "Skip downloading. Read every CSV/XLSX file in the data directory "
            "and load directly to the database. "
            "Use --period YYYYMM when filenames don't encode the date."
        ),
    )
    args = parser.parse_args()

    run(period_yyyymm=args.period, dry_run=args.dry_run, local=args.local)


if __name__ == "__main__":
    main()
