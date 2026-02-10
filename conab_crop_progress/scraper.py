"""URL discovery and file download for CONAB crop progress reports."""

from __future__ import annotations

import json
import logging
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .config import (
    ARCHIVE_ZIPS,
    CONAB_LISTING_BASE,
    METADATA_DIR,
    RAW_DIR,
    REQUEST_DELAY_SECONDS,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
    SCRAPE_LOG_PATH,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scrape log helpers
# ---------------------------------------------------------------------------

def get_scrape_log() -> dict:
    """Load the scrape log (downloaded URLs + timestamps)."""
    if SCRAPE_LOG_PATH.exists():
        return json.loads(SCRAPE_LOG_PATH.read_text(encoding="utf-8"))
    return {"downloaded": {}}


def update_scrape_log(url: str, dest: str) -> None:
    """Record a successful download in the scrape log."""
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    log = get_scrape_log()
    log["downloaded"][url] = {
        "path": str(dest),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    SCRAPE_LOG_PATH.write_text(
        json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Generic download
# ---------------------------------------------------------------------------

def download_file(url: str, dest: Path, *, force: bool = False) -> Path:
    """Download a file with retry logic. Skip if already exists unless force=True."""
    if dest.exists() and not force:
        logger.debug("Skipping (already exists): %s", dest)
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s -> %s", url, dest)

    for attempt in range(1, 4):
        try:
            resp = requests.get(
                url,
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT,
                stream=True,
            )
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    f.write(chunk)
            update_scrape_log(url, str(dest))
            return dest
        except requests.RequestException as exc:
            logger.warning(
                "Attempt %d failed for %s: %s", attempt, url, exc
            )
            if attempt < 3:
                time.sleep(2 ** attempt)
            else:
                raise

    return dest  # unreachable, keeps type-checker happy


# ---------------------------------------------------------------------------
# 2020-2024: ZIP archives
# ---------------------------------------------------------------------------

def download_archives(
    years: list[int] | None = None, *, force: bool = False
) -> list[Path]:
    """Download yearly ZIP archives and extract Excel files.

    Returns list of extracted .xlsx paths.
    """
    if years is None:
        years = sorted(ARCHIVE_ZIPS.keys())

    extracted: list[Path] = []

    for year in years:
        url = ARCHIVE_ZIPS.get(year)
        if url is None:
            logger.warning("No archive URL configured for year %d", year)
            continue

        year_dir = RAW_DIR / str(year)
        zip_path = RAW_DIR / f"{year}.zip"

        # Check if already extracted
        if year_dir.exists() and any(year_dir.glob("*.xlsx")) and not force:
            logger.info("Year %d already extracted, skipping", year)
            extracted.extend(sorted(year_dir.glob("*.xlsx")))
            continue

        download_file(url, zip_path, force=force)

        # Extract xlsx files only
        year_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                if member.lower().endswith(".xlsx") and not member.startswith(
                    "__MACOSX"
                ):
                    # Flatten nested paths: just use the filename
                    filename = Path(member).name
                    target = year_dir / filename
                    with zf.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())
                    extracted.append(target)
                    logger.debug("Extracted: %s", target)

        logger.info(
            "Year %d: extracted %d files",
            year,
            len(list(year_dir.glob("*.xlsx"))),
        )
        time.sleep(REQUEST_DELAY_SECONDS)

    return sorted(extracted)


# ---------------------------------------------------------------------------
# 2025+: Discover individual files from Plone CMS listing
# ---------------------------------------------------------------------------

def discover_2025_urls() -> list[dict]:
    """Crawl the CONAB Plone CMS listing pages to find crop progress file URLs.

    Returns list of dicts with keys: url, title, year.
    """
    discovered: list[dict] = []
    seen_urls: set[str] = set()
    offset = 0
    page_size = 20
    max_pages = 50  # safety limit

    for page in range(max_pages):
        params = {"b_start:int": str(offset)}
        logger.info("Fetching listing page offset=%d", offset)

        try:
            resp = requests.get(
                CONAB_LISTING_BASE,
                params=params,
                headers=REQUEST_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Failed to fetch listing page: %s", exc)
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        # Find links matching "plantio-e-colheita" pattern
        links = soup.find_all("a", href=True)
        page_found = 0
        for link in links:
            href: str = link["href"]
            if "plantio-e-colheita" not in href.lower():
                continue

            # Construct download URL
            if "@@download" not in href:
                download_url = href.rstrip("/") + "/@@download/file"
            else:
                download_url = href

            if not download_url.startswith("http"):
                download_url = "https://www.conab.gov.br" + download_url

            if download_url in seen_urls:
                continue
            seen_urls.add(download_url)

            title = link.get_text(strip=True) or Path(href).stem
            # Try to extract year from URL path
            year = _extract_year_from_url(href)
            discovered.append(
                {"url": download_url, "title": title, "year": year}
            )
            page_found += 1

        if page_found == 0:
            logger.info("No more links found at offset=%d, stopping", offset)
            break

        offset += page_size
        time.sleep(REQUEST_DELAY_SECONDS)

    logger.info("Discovered %d file URLs for 2025+", len(discovered))
    return discovered


def _extract_year_from_url(url: str) -> int:
    """Best-effort year extraction from a URL path."""
    import re

    # Look for 4-digit year in URL
    match = re.search(r"/(\d{4})/", url)
    if match:
        return int(match.group(1))
    # Look for year in filename-like segments
    match = re.search(r"20[2-3]\d", url)
    if match:
        return int(match.group(0))
    return datetime.now().year


def download_2025_files(*, force: bool = False) -> list[Path]:
    """Discover and download all 2025+ individual Excel files.

    Returns list of downloaded .xlsx paths.
    """
    entries = discover_2025_urls()
    downloaded: list[Path] = []

    for entry in entries:
        year = entry["year"]
        year_dir = RAW_DIR / str(year)
        year_dir.mkdir(parents=True, exist_ok=True)

        # Derive filename from title or URL
        filename = _safe_filename(entry["title"], entry["url"])
        dest = year_dir / filename

        try:
            download_file(entry["url"], dest, force=force)
            downloaded.append(dest)
        except requests.RequestException as exc:
            logger.error("Failed to download %s: %s", entry["url"], exc)

        time.sleep(REQUEST_DELAY_SECONDS)

    return sorted(downloaded)


def _safe_filename(title: str, url: str) -> str:
    """Generate a safe filename from a title or URL."""
    import re

    # Prefer the last path segment of the URL
    segment = url.split("/")[-1] if "@@download" not in url.split("/")[-1] else url.split("/")[-3]
    # Clean up
    name = re.sub(r"[^\w\s\-.]", "", segment)
    name = name.strip()
    if not name or name == "file":
        name = re.sub(r"[^\w\s\-.]", "", title)
        name = name.strip()[:80]
    if not name.lower().endswith(".xlsx"):
        name += ".xlsx"
    return name
