"""Pipeline orchestration: scrape -> parse -> export."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .config import ARCHIVE_ZIPS, OUTPUT_DIR, RAW_DIR
from .parser import parse_directory, parse_file
from .scraper import download_2025_files, download_archives

logger = logging.getLogger(__name__)


def run_pipeline(
    years: list[int] | None = None,
    *,
    force: bool = False,
    output_dir: Path | str | None = None,
    skip_download: bool = False,
) -> pd.DataFrame:
    """Run the full ETL pipeline.

    1. Download/extract files (unless skip_download)
    2. Parse all Excel files
    3. Build DataFrame, translate, enrich
    4. Export to Parquet + CSV
    5. Print summary stats

    Returns the final DataFrame.
    """
    output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # ----- Step 1: Download -----
    if not skip_download:
        archive_years = [y for y in (years or ARCHIVE_ZIPS.keys()) if y <= 2024]
        if archive_years:
            logger.info("Downloading archives for years: %s", archive_years)
            download_archives(archive_years, force=force)

        if years is None or any(y >= 2025 for y in years):
            logger.info("Discovering and downloading 2025+ files...")
            download_2025_files(force=force)

    # ----- Step 2: Parse -----
    logger.info("Parsing all downloaded files...")
    if years:
        all_records: list[dict] = []
        for year in years:
            year_dir = RAW_DIR / str(year)
            if year_dir.exists():
                all_records.extend(parse_directory(year_dir))
    else:
        all_records = parse_directory(RAW_DIR)

    if not all_records:
        logger.warning("No records parsed. Check raw data directory: %s", RAW_DIR)
        return pd.DataFrame()

    # ----- Step 3: Build DataFrame -----
    df = pd.DataFrame(all_records)

    # Coerce date columns
    for col in ("report_date", "week_start", "week_end"):
        df[col] = pd.to_datetime(df[col]).dt.date

    # Deduplicate: some files contain the same crop block twice
    dup_cols = ["report_date", "crop", "crop_season", "activity", "state"]
    before = len(df)
    df = df.drop_duplicates(subset=dup_cols, keep="first")
    dropped = before - len(df)
    if dropped:
        logger.info("Dropped %d duplicate rows", dropped)

    # Sort
    df = df.sort_values(
        ["report_date", "crop", "activity", "state"]
    ).reset_index(drop=True)

    # ----- Step 4: Export -----
    parquet_path = output_dir / "conab_crop_progress.parquet"
    csv_path = output_dir / "conab_crop_progress.csv"

    df.to_parquet(parquet_path, index=False, engine="pyarrow")
    logger.info("Exported Parquet: %s (%d rows)", parquet_path, len(df))

    df.to_csv(csv_path, index=False)
    logger.info("Exported CSV: %s (%d rows)", csv_path, len(df))

    # ----- Step 5: Summary -----
    _print_summary(df)

    return df


def parse_only(
    raw_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> pd.DataFrame:
    """Re-parse already-downloaded files without downloading."""
    return run_pipeline(
        skip_download=True,
        output_dir=output_dir,
    )


def _print_summary(df: pd.DataFrame) -> None:
    """Print summary statistics of the dataset."""
    print("\n" + "=" * 60)
    print("CONAB Crop Progress - Pipeline Summary")
    print("=" * 60)
    print(f"Total records:       {len(df):,}")
    print(f"Date range:          {df['report_date'].min()} to {df['report_date'].max()}")
    print(f"Crops:               {sorted(df['crop'].unique())}")
    print(f"Activities:          {sorted(df['activity'].unique())}")
    print(f"States:              {df['state'].nunique()} unique")
    print(f"Source files:        {df['source_file'].nunique()} files")

    print("\nRecords per crop & activity:")
    summary = (
        df.groupby(["crop", "activity"])
        .agg(
            records=("report_date", "count"),
            min_date=("report_date", "min"),
            max_date=("report_date", "max"),
        )
        .reset_index()
    )
    print(summary.to_string(index=False))
    print("=" * 60 + "\n")
