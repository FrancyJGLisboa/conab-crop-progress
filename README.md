# CONAB Crop Progress ETL Pipeline

A Python ETL pipeline that scrapes, parses, and normalizes Brazilian crop progress data from [CONAB](https://www.gov.br/conab/) (Companhia Nacional de Abastecimento) into a single tidy tabular dataset in English, following USDA crop progress conventions.

CONAB publishes weekly crop progress reports for Brazil's major crops at the state level, but the data is trapped in non-standard Excel spreadsheets across hundreds of individual files and ZIP archives. This pipeline consolidates everything into machine-readable Parquet and CSV formats.

## Why This Matters

USDA publishes US crop progress weekly in clean CSVs. Brazil — the world's largest soybean exporter and #3 corn exporter — had no equivalent machine-readable dataset. Anyone making decisions about global grain markets was either manually reading CONAB PDFs/Excel files or flying blind on Brazilian crop timing. This dataset changes that.

### Commodity Trading & Price Forecasting
- **Real-time supply signals**: Planting delays or harvest acceleration directly impact futures prices (CBOT soybeans, corn, etc.). A trader seeing MT soybeans planting 10% behind the 5-year average in November can position ahead of the market.
- **Basis trading**: State-level granularity lets you estimate regional supply bottlenecks — e.g., if Paraná harvest is lagging while Mato Grosso is ahead, that affects port logistics and local basis.
- **Cross-country arbitrage**: Compare Brazil's planting/harvest pace against USDA weekly crop progress for the US to forecast global supply shifts.

### Logistics & Supply Chain
- **Port and rail capacity planning**: Knowing that soybeans harvest in MT peaks 2-3 weeks before PR means you can anticipate when Santos vs Paranaguá ports will be under pressure.
- **Trucking and storage**: Corn 2 (safrinha) harvest overlapping with soybean exports creates the infamous Brazilian logistics crunch every Jul-Aug. This data quantifies the timing precisely.
- **Crush margin optimization**: Soy processors can plan capacity utilization based on when raw soybeans will actually arrive from each state.

### Agricultural Insurance & Credit
- **Crop failure early warning**: If a state's planting progress stalls (e.g., drought in RS), insurers can start reserving for claims weeks before official loss reports.
- **Credit risk assessment**: Banks financing farmers can flag regions where planting is abnormally late — higher probability of replanting costs or yield loss.

### Government & Policy
- **Food security monitoring**: Track whether staple crops (rice, dry beans) are on pace for domestic consumption needs.
- **Export quota/tax decisions**: Brazil periodically considers export restrictions — this data provides the evidence base for whether supply will be tight.

### Agribusiness Strategy
- **Input timing**: Seed, fertilizer, and agrochemical companies can time regional sales campaigns to actual planting windows rather than calendar estimates.
- **Competitive intelligence**: Compare current season vs historical to identify structural shifts — e.g., cotton acreage expanding into new states, or corn 2 planting window getting tighter year over year.

### Quantitative Research
- **Yield modeling**: Combine progress pace with satellite NDVI and weather data to build state-level yield forecasts — faster planting under good conditions correlates with higher yields.
- **Climate trend analysis**: 4+ years of weekly data lets you detect whether planting windows are shifting due to changing rainfall patterns.

## Output Dataset

**15,600+ records** covering 2022-present, with weekly updates for 7 crops across 13 Brazilian states.

### Schema

| Column | Type | Description |
|---|---|---|
| `report_date` | date | End date of the reporting week (YYYY-MM-DD) |
| `week_start` | date | Start of monitoring week |
| `week_end` | date | End of monitoring week |
| `crop` | string | English crop name (see table below) |
| `crop_season` | string | Crop season label (e.g., "2025/26") |
| `activity` | string | `"planting"` or `"harvest"` |
| `state` | string | Brazilian state name (e.g., "Mato Grosso") |
| `state_code` | string | ISO 3166-2:BR code (e.g., "MT") |
| `is_total` | bool | True if this is the aggregate row for all states |
| `progress_pct` | float | Progress percentage (0.0-1.0) for current week |
| `prev_week_pct` | float | Progress percentage for previous week |
| `prev_year_pct` | float | Progress percentage for same week in previous year |
| `five_year_avg_pct` | float | 5-year average for same week (nullable, 2025+ only) |
| `source_file` | string | Source filename for traceability |

### Crops

| Portuguese | English Key | Notes |
|---|---|---|
| Algodao | `cotton` | |
| Arroz | `rice` | |
| Feijao 1a | `dry_beans_1` | First crop |
| Milho 1a | `corn_1` | First crop |
| Milho 2a | `corn_2` | Safrinha |
| Soja | `soybeans` | |
| Trigo | `wheat` | Single-year season |

## Installation

```bash
# Clone the repository
git clone https://github.com/FrancyJGLisboa/conab-crop-progress.git
cd conab-crop-progress

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Dependencies

- `requests` - HTTP downloads
- `openpyxl` - Excel parsing
- `pandas` - Data manipulation
- `pyarrow` - Parquet export
- `click` - CLI framework
- `beautifulsoup4` - HTML parsing for web scraping

## Usage

### CLI Commands

```bash
# Full backfill: download all years (2020-2025+) and process
conab-crop-progress backfill

# Backfill specific years
conab-crop-progress backfill --years 2023,2024

# Incremental update: fetch only new data since last run
conab-crop-progress update

# Re-parse already downloaded files (no network requests)
conab-crop-progress parse-only

# Export in specific formats
conab-crop-progress export --format parquet,csv

# Enable verbose/debug logging
conab-crop-progress -v backfill
```

### Options

| Command | Flag | Description |
|---|---|---|
| `backfill` | `--years` | Comma-separated years (default: all) |
| `backfill` | `--force` | Re-download even if files exist |
| `backfill` | `--output` | Custom output directory |
| `update` | `--force` | Force re-download |
| `parse-only` | `--raw-dir` | Custom raw data directory |
| `export` | `--format` | Output formats: `parquet`, `csv` |

### Python API

```python
from conab_crop_progress.pipeline import run_pipeline

# Run full pipeline, returns a pandas DataFrame
df = run_pipeline(years=[2024], skip_download=False)

# Parse already-downloaded files
from conab_crop_progress.parser import parse_file
records = parse_file("data/raw/2024/PlantioZeZColheitaZ01-01ZaZ07-01.xlsx")

# Work with the output directly
import pandas as pd
df = pd.read_parquet("data/output/conab_crop_progress.parquet")
```

## Data Sources

### 2020-2024: ZIP Archives

Yearly ZIP archives hosted on `arquivosportal.conab.gov.br`, each containing weekly Excel spreadsheets.

| Year | Files | Notes |
|---|---|---|
| 2020 | 8 | "Acompanhamento semanal" format (limited parsing) |
| 2021 | 8 | "Acompanhamento semanal" format (limited parsing) |
| 2022 | 72 | Mix of "Plantio e Colheita" + "Fenologia" files |
| 2023 | 104 | Mix of "Plantio e Colheita" + "Fenologia" files |
| 2024 | 53 | "Plantio e Colheita" files |

### 2025+: Individual Files via gov.br

Individual Excel files discovered by crawling the [CONAB Progresso de Safra](https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/safras/progresso-de-safra) Plone CMS listing pages. The scraper paginates through results and downloads files matching the `plantio-e-colheita` URL pattern.

## Project Structure

```
conab-crop-progress/
├── README.md
├── pyproject.toml              # Project metadata + dependencies
├── conab_crop_progress/
│   ├── __init__.py
│   ├── cli.py                  # CLI entrypoint (click)
│   ├── scraper.py              # URL discovery + file download
│   ├── parser.py               # Excel parsing (row-by-row state machine)
│   ├── translator.py           # PT->EN mappings (crops, states, activities)
│   ├── pipeline.py             # Orchestrator: scrape -> parse -> export
│   └── config.py               # Constants, URLs, paths
├── data/
│   ├── raw/                    # Downloaded Excel files (gitignored)
│   ├── output/                 # Parquet + CSV output (gitignored)
│   └── metadata/               # Scrape log (gitignored)
└── tests/
    ├── __init__.py
    └── test_parser.py          # Unit + integration tests
```

## How Parsing Works

Each CONAB Excel file contains one sheet with multiple crop blocks stacked vertically. The parser uses a **row-by-row state machine** that:

1. **Detects crop headers** via regex: `"Soja - Safra 2025/26"` pattern
2. **Detects activity rows**: "Semeadura" (planting) or "Colheita" (harvest)
3. **Parses date header rows** to extract reference dates
4. **Extracts state data rows** with percentage values
5. **Handles edge cases**: merged cells, string annotations (`"0,5% **"`), varying column counts, and format differences between years

Key design decisions:
- **Heuristic detection** (not fixed row positions) to handle format variations across years
- **Smart percentage coercion**: openpyxl returns Excel percentage-formatted cells as 0-1 decimals (used as-is); string annotations like `"0,5% **"` are divided by 100
- **Graceful skipping** of non-Plantio files (Fenologia, Acompanhamento) and corrupt files

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Unit tests cover:
# - Percentage coercion (int, float, string with commas, annotations)
# - Crop name normalization (Portuguese -> English)
# - Activity normalization (handles asterisks, whitespace)
# - State name -> ISO code mapping

# Integration tests (require downloaded data in data/raw/):
# - Parse real files, validate schema
# - Check progress values are in [0, 1]
# - Verify state codes are valid 2-letter codes
```

## Automated Updates

A GitHub Actions workflow runs **every Monday and Thursday at 14:00 UTC**, automatically:

1. Restoring cached raw data from previous runs
2. Running the full pipeline (downloads only new files, skips existing)
3. Committing updated CSV + Parquet to the repo if new data is found

This means the output files in `data/output/` are always up-to-date — no manual intervention needed. You can also trigger it manually from the **Actions** tab.

The workflow uses GitHub's free tier (unlimited for public repos, 2,000 min/month for private). Each run takes ~3 minutes.

## Known Limitations

- **2020-2021 data**: These years used a different spreadsheet format ("Acompanhamento semanal das lavouras") that the parser does not currently extract crop progress from. The effective data range starts from 2022.
- **Footnoted values**: A few cells contain footnote annotations like `"15% (1)"` or `"85,8% ⁽¹⁾"` — these are parsed correctly via regex, but edge cases may exist.
- **Seasonal crops**: Some crops (Feijao 2a/3a, corn_2) only appear during their respective seasons, so coverage is not year-round.

## License

This project scrapes publicly available government data from CONAB. The pipeline code is provided as-is for research and analysis purposes.
