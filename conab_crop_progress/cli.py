"""CLI entrypoint for the CONAB crop progress pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from .config import ARCHIVE_ZIPS, OUTPUT_DIR, RAW_DIR


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
def main(verbose: bool) -> None:
    """CONAB Crop Progress ETL Pipeline.

    Scrape, parse, and export Brazilian crop progress data from CONAB
    into tidy Parquet/CSV datasets.
    """
    _setup_logging(verbose)


@main.command()
@click.option(
    "--years",
    type=str,
    default=None,
    help="Comma-separated years to process (default: all available).",
)
@click.option("--force", is_flag=True, help="Re-download even if files exist.")
@click.option(
    "--output",
    type=click.Path(),
    default=None,
    help=f"Output directory (default: {OUTPUT_DIR}).",
)
def backfill(years: str | None, force: bool, output: str | None) -> None:
    """Download all historical data and process it."""
    from .pipeline import run_pipeline

    year_list = _parse_years(years)
    run_pipeline(years=year_list, force=force, output_dir=output)


@main.command()
@click.option("--force", is_flag=True, help="Re-download even if files exist.")
@click.option(
    "--output",
    type=click.Path(),
    default=None,
    help=f"Output directory (default: {OUTPUT_DIR}).",
)
def update(force: bool, output: str | None) -> None:
    """Fetch only new weeks since last run (incremental)."""
    from .pipeline import run_pipeline

    # Update only fetches 2025+ and the current archive year
    current_year = 2025  # For 2025+ individual files
    run_pipeline(years=None, force=force, output_dir=output)


@main.command("parse-only")
@click.option(
    "--raw-dir",
    type=click.Path(exists=True),
    default=None,
    help=f"Raw data directory (default: {RAW_DIR}).",
)
@click.option(
    "--output",
    type=click.Path(),
    default=None,
    help=f"Output directory (default: {OUTPUT_DIR}).",
)
def parse_only(raw_dir: str | None, output: str | None) -> None:
    """Re-parse already-downloaded files without downloading."""
    from .pipeline import parse_only as _parse_only

    _parse_only(raw_dir=raw_dir, output_dir=output)


@main.command()
@click.option(
    "--format",
    "formats",
    type=str,
    default="parquet,csv",
    help="Comma-separated output formats (parquet, csv).",
)
@click.option(
    "--output",
    type=click.Path(),
    default=None,
    help=f"Output directory (default: {OUTPUT_DIR}).",
)
def export(formats: str, output: str | None) -> None:
    """Export parsed data in specified formats."""
    import pandas as pd

    from .config import OUTPUT_DIR as _default_output

    output_dir = Path(output) if output else _default_output
    parquet_path = output_dir / "conab_crop_progress.parquet"

    if not parquet_path.exists():
        click.echo(
            "No parquet file found. Run 'backfill' or 'parse-only' first.",
            err=True,
        )
        raise SystemExit(1)

    df = pd.read_parquet(parquet_path)
    fmt_list = [f.strip().lower() for f in formats.split(",")]

    for fmt in fmt_list:
        if fmt == "parquet":
            dest = output_dir / "conab_crop_progress.parquet"
            df.to_parquet(dest, index=False, engine="pyarrow")
            click.echo(f"Exported: {dest}")
        elif fmt == "csv":
            dest = output_dir / "conab_crop_progress.csv"
            df.to_csv(dest, index=False)
            click.echo(f"Exported: {dest}")
        else:
            click.echo(f"Unknown format: {fmt}", err=True)


def _parse_years(years_str: str | None) -> list[int] | None:
    """Parse a comma-separated year string into a list of ints."""
    if years_str is None:
        return None
    return [int(y.strip()) for y in years_str.split(",") if y.strip()]


if __name__ == "__main__":
    main()
