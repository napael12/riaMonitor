"""
parser.py — Parse SEC IAPD bulk data files into normalised DataFrames.

Column mapping is driven by etl/mapping.json:
  [{"file": "<exact column name in file>", "db": "<database column>"}]

Supports both .xlsx and .csv input files.
"""

import json
from pathlib import Path
from typing import Optional

import pandas as pd

MAPPING_PATH = Path(__file__).parent / "mapping.json"

# DB columns that should be cast to numeric
_NUMERIC_COLS = {"aum", "employees", "num_clients"}

# DB columns that should be cast to integer (subset of numeric)
_INT_COLS = {"employees", "num_clients"}


def _load_mapping() -> dict[str, str]:
    """
    Load mapping.json and return a dict of {file_col_lower: db_col}.
    Matching is case-insensitive and whitespace-stripped.
    """
    with open(MAPPING_PATH, encoding="utf-8") as fh:
        entries = json.load(fh)
    return {e["file"].strip().lower(): e["db"] for e in entries}


def _read_file(path: Path) -> pd.DataFrame:
    """Read .xlsx or .csv into a DataFrame (all values as strings)."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return pd.read_csv(str(path), dtype=str, encoding=enc, low_memory=False)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not decode {path.name} with utf-8-sig, cp1252, or latin-1")
    return pd.read_excel(str(path), engine="openpyxl", dtype=str)


def parse_file(path: Path, registration_type: str) -> pd.DataFrame:
    """
    Read an SEC IAPD data file and return a normalised DataFrame with columns:
        crd, firm_name, sec_number, primary_state, aum, employees,
        num_clients, registration_status, registration_type, raw

    Parameters
    ----------
    path : Path
        Local path to the .xlsx or .csv file.
    registration_type : str
        Either ``'SEC'`` or ``'Exempt'`` — stored verbatim in the output.
    """
    path = Path(path)
    print(f"[parser] Reading {path.name} …")

    mapping = _load_mapping()   # {file_col_lower: db_col}

    raw_df = _read_file(path)

    # Build lookup: file_col_lower → original_col_name (cast to str for safety)
    col_lookup: dict[str, str] = {
        str(col).strip().lower(): str(col) for col in raw_df.columns
    }

    # Map each file column to its db column where the mapping entry matches
    # file_col_lower → db_col
    file_to_db: dict[str, str] = {}
    for file_col_lower, db_col in mapping.items():
        if file_col_lower in col_lookup:
            file_to_db[col_lookup[file_col_lower]] = db_col

    # Warn about unmapped db columns
    mapped_db_cols = set(file_to_db.values())
    all_db_cols = {"crd", "firm_name", "sec_number", "primary_state",
                   "aum", "employees", "num_clients", "registration_status"}
    missing = all_db_cols - mapped_db_cols
    if missing:
        print(f"[parser] Warning — no mapping found for db columns: {sorted(missing)}")
    if "crd" not in mapped_db_cols:
        raise ValueError(
            f"mapping.json has no entry whose 'file' column exists in {path.name}. "
            f"Available columns (first 10): {[str(c) for c in raw_df.columns][0:10]}"
        )

    # Build output columns from mapping
    out: dict[str, pd.Series] = {}
    for orig_col, db_col in file_to_db.items():
        out[db_col] = raw_df[orig_col]

    # Fill any db columns missing from mapping with None
    for db_col in all_db_cols:
        if db_col not in out:
            out[db_col] = pd.Series([None] * len(raw_df), dtype=object)

    out_df = pd.DataFrame(out)

    # Coerce numeric columns
    for col in _NUMERIC_COLS:
        out_df[col] = pd.to_numeric(out_df[col], errors="coerce")

    # Round integer columns
    for col in _INT_COLS:
        out_df[col] = out_df[col].where(out_df[col].isna(), out_df[col].round().astype("Int64"))

    # Strip whitespace from string columns
    for col in all_db_cols - _NUMERIC_COLS:
        out_df[col] = out_df[col].astype(str).str.strip()
        out_df[col] = out_df[col].replace({"nan": None, "None": None, "": None})

    out_df["registration_type"] = registration_type

    # Build raw JSON column (all original columns as a dict per row)
    def _row_to_json(row: pd.Series) -> str:
        import json as _json
        return _json.dumps(
            {k: (None if pd.isna(v) else str(v)) for k, v in row.items()}
        )

    out_df["raw"] = raw_df.apply(_row_to_json, axis=1)

    # Drop rows where CRD is null or empty
    out_df = out_df.dropna(subset=["crd"])
    out_df = out_df[out_df["crd"].str.strip() != ""]

    # Ensure column order
    out_df = out_df[[
        "crd", "firm_name", "sec_number", "primary_state",
        "aum", "employees", "num_clients", "registration_status",
        "registration_type", "raw",
    ]]

    print(f"[parser] Parsed {len(out_df):,} rows from {path.name}")
    return out_df


# Backward-compatible alias (pipeline.py calls parse_xlsx)
def parse_xlsx(path: Path, registration_type: str) -> pd.DataFrame:
    return parse_file(path, registration_type)
