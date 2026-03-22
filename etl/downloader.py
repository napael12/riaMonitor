"""
downloader.py — Scrape the SEC IAPD page for investment adviser bulk download files
using a Selenium headless Chrome browser, then download them to a local cache directory.

Links are identified by their visible <a> tag text containing 'MMMM YYYY'
(e.g. "Registered Investment Advisers, March 2026" or "Exempt Reporting Advisers, March 2026").
"""

import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

SEC_PAGE_URL = (
    "https://www.sec.gov/data-research/sec-markets-data/"
    "information-about-registered-investment-advisers-exempt-reporting-advisers"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IAMonitor/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}

# Matches a full month name followed by a 4-digit year at the end of link text
# e.g. "Registered Investment Advisers, March 2026" → ("March", "2026")
_RE_MONTH_YEAR = re.compile(r"\b([A-Za-z]+)\s+(\d{4})\s*$")


def _build_driver() -> webdriver.Chrome:
    """
    Create a headless Chrome WebDriver.

    Respects two optional environment variables for Docker / CI environments:
      CHROME_BINARY_PATH   — path to the Chrome/Chromium executable
      CHROMEDRIVER_PATH    — path to the matching chromedriver binary

    If CHROMEDRIVER_PATH is not set, webdriver-manager downloads the correct
    driver automatically (useful for local development).
    """
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(f"user-agent={HEADERS['User-Agent']}")

    chrome_binary = os.environ.get("CHROME_BINARY_PATH")
    if chrome_binary:
        opts.binary_location = chrome_binary

    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
    if chromedriver_path:
        service = Service(chromedriver_path)
    else:
        # Lazy import so webdriver-manager is only required when no system driver
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())

    return webdriver.Chrome(service=service, options=opts)


def _scrape_all_urls(page_url: str) -> tuple[dict[str, str], dict[str, str]]:
    """
    Use Selenium headless Chrome to load the SEC IAPD page and collect all
    download links whose visible text contains a 'MMMM YYYY' date.

    Registered links are those whose text does NOT contain "exempt" (case-insensitive).
    Exempt links are those whose text or href contains "exempt".

    Returns:
        (registered, exempt) — each a dict mapping {YYYY-MM period: absolute URL}
    """
    print(f"[downloader] Launching headless Chrome to load: {page_url}")
    driver = _build_driver()
    try:
        driver.get(page_url)

        # Wait up to 30 s for at least one <a download> link to appear
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[download]"))
            )
        except Exception:
            # Fallback: wait for any <a> with an href containing the data path
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//a[contains(@href,'investment-advisers')]")
                )
            )

        links = driver.find_elements(By.TAG_NAME, "a")

        registered: dict[str, str] = {}
        exempt: dict[str, str] = {}

        for link in links:
            text = (link.text or "").strip()
            href = link.get_attribute("href") or ""

            # Only process links whose text ends with 'MMMM YYYY'
            m = _RE_MONTH_YEAR.search(text)
            if not m:
                continue

            month_name, year_str = m.group(1), m.group(2)
            try:
                period = datetime.strptime(
                    f"{month_name} {year_str}", "%B %Y"
                ).strftime("%Y-%m")
            except ValueError:
                continue  # unrecognised month name

            # Resolve relative URLs
            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                url = f"https://www.sec.gov{href}"
            else:
                continue

            if "exempt" in text.lower() or "exempt" in href.lower():
                exempt[period] = url
            else:
                registered[period] = url

    finally:
        driver.quit()

    return registered, exempt


def get_latest_urls(page_url: str = SEC_PAGE_URL) -> dict[str, str]:
    """
    Return URLs for the most recent registered and exempt files found on the page.

    Returns:
        {"registered": "<url>", "exempt": "<url>"}
    """
    registered, exempt = _scrape_all_urls(page_url)

    if not registered:
        raise ValueError(f"No registered adviser download links found on page: {page_url}")
    if not exempt:
        raise ValueError(f"No exempt adviser download links found on page: {page_url}")

    # YYYY-MM keys sort correctly lexicographically
    return {
        "registered": registered[max(registered.keys())],
        "exempt":     exempt[max(exempt.keys())],
    }


def get_urls_for_period(period_yyyymm: str, page_url: str = SEC_PAGE_URL) -> dict[str, str]:
    """
    Return URLs for the registered and exempt files for a specific period.

    period_yyyymm: six-digit string in yyyyMM format, e.g. ``"202603"`` for March 2026.

    The link text on the SEC page reads e.g. "Registered Investment Advisers, March 2026",
    so this function converts the period to 'MMMM YYYY' and matches accordingly.

    Returns:
        {"registered": "<url>", "exempt": "<url>"}

    Raises:
        ValueError: if no links are found for the given period.
    """
    if not re.match(r"^\d{6}$", period_yyyymm):
        raise ValueError(
            f"period must be in yyyyMM format (e.g. 202603), got: {period_yyyymm!r}"
        )

    # Convert "202603" → "2026-03" for dict lookup
    period_key = f"{period_yyyymm[:4]}-{period_yyyymm[4:]}"

    registered, exempt = _scrape_all_urls(page_url)

    if period_key not in registered:
        raise ValueError(
            f"No registered adviser link found for period {period_yyyymm} "
            f"(looked for YYYY-MM={period_key!r}) on page: {page_url}"
        )
    if period_key not in exempt:
        raise ValueError(
            f"No exempt adviser link found for period {period_yyyymm} "
            f"(looked for YYYY-MM={period_key!r}) on page: {page_url}"
        )

    return {
        "registered": registered[period_key],
        "exempt":     exempt[period_key],
    }


def download_file(url: str, dest_dir: Path) -> Path:
    """
    Download *url* into *dest_dir*, skipping if the file already exists
    (cache by filename).

    If the downloaded file is a .zip archive, it is extracted in place and
    the path to the first .xlsx or .csv file found inside is returned.

    Returns the local Path of the (possibly extracted) data file.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    filename = url.split("/")[-1].split("?")[0]  # strip query string if any
    dest_path = dest_dir / filename

    if not dest_path.exists():
        print(f"[downloader] Downloading {url} …")
        with requests.get(url, headers=HEADERS, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(dest_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):  # 1 MB
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r  {pct:.1f}%", end="", flush=True)
        print(f"\n[downloader] Saved → {dest_path}")
    else:
        print(f"[downloader] Cache hit — skipping download: {dest_path}")

    # If the downloaded file is a zip, extract it and return the inner data file
    if dest_path.suffix.lower() == ".zip":
        return _extract_zip(dest_path, dest_dir)

    return dest_path


def _extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    """
    Extract the first .xlsx or .csv file from *zip_path* into *dest_dir*.

    Returns the path to the extracted file.  Skips extraction if the target
    already exists (cache-safe).
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = [
            m for m in zf.namelist()
            if m.lower().endswith((".xlsx", ".csv")) and not m.startswith("__MACOSX")
        ]
        if not members:
            raise ValueError(
                f"No .xlsx or .csv file found inside zip archive: {zip_path}"
            )

        # Use the first match (zips typically contain a single data file)
        member_name = members[0]
        extracted_name = Path(member_name).name
        extracted_path = dest_dir / extracted_name

        if extracted_path.exists():
            print(f"[downloader] Cache hit — skipping extraction: {extracted_path}")
            return extracted_path

        with zf.open(member_name) as src, open(extracted_path, "wb") as dst:
            dst.write(src.read())

    print(f"[downloader] Extracted → {extracted_path}")
    return extracted_path


def date_str_to_period(filename: str) -> Optional[str]:
    """
    Convert a filename like ``ia032526.xlsx``, ``ia032526-exempt.xlsx``,
    or ``ia032526-exempt.zip`` to a period string ``YYYY-MM``.

    The SEC uses MMDDYY encoding in filenames.
    Returns None if the filename doesn't match the expected pattern.
    """
    m = re.search(r"ia(\d{2})(\d{2})(\d{2})", filename)
    if not m:
        return None
    mm, dd, yy = m.group(1), m.group(2), m.group(3)
    year = int(yy) + 2000  # works until 2099
    return f"{year:04d}-{mm}"
