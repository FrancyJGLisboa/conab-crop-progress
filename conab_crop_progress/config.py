"""Constants, URLs, and configuration for the CONAB crop progress pipeline."""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = DATA_DIR / "output"
METADATA_DIR = DATA_DIR / "metadata"
SCRAPE_LOG_PATH = METADATA_DIR / "scrape_log.json"

# ---------------------------------------------------------------------------
# Archive ZIP URLs (2020-2024)
# ---------------------------------------------------------------------------
ARCHIVE_ZIPS: dict[int, str] = {
    2024: "https://arquivosportal.conab.gov.br/api/public/dl/__RgwV3s/progressodesafra/2024.zip",
    2023: "https://arquivosportal.conab.gov.br/api/public/dl/oTQZ6N06/progressodesafra/2023.zip",
    2022: "https://arquivosportal.conab.gov.br/api/public/dl/lvdzd4M6/progressodesafra/2022.zip",
    2021: "https://arquivosportal.conab.gov.br/api/public/dl/9ODssP_0/progressodesafra/2021.zip",
    2020: "https://arquivosportal.conab.gov.br/api/public/dl/Vpz9veNH/progressodesafra/2020.zip",
}

# Base URL for 2025+ individual file discovery (moved to gov.br Plone CMS)
CONAB_LISTING_BASE = (
    "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias"
    "/safras/progresso-de-safra"
)

# ---------------------------------------------------------------------------
# Crop name mapping  (Portuguese -> English key)
# ---------------------------------------------------------------------------
CROP_MAP: dict[str, str] = {
    "Algodão": "cotton",
    "Arroz": "rice",
    "Feijão 1ª": "dry_beans_1",
    "Feijão 2ª": "dry_beans_2",
    "Feijão 3ª": "dry_beans_3",
    "Milho 1ª": "corn_1",
    "Milho 2ª": "corn_2",
    "Soja": "soybeans",
    "Trigo": "wheat",
}

# ---------------------------------------------------------------------------
# Activity mapping
# ---------------------------------------------------------------------------
ACTIVITY_MAP: dict[str, str] = {
    "Semeadura": "planting",
    "Colheita": "harvest",
}

# ---------------------------------------------------------------------------
# Brazilian state name -> ISO 3166-2:BR code
# ---------------------------------------------------------------------------
STATE_MAP: dict[str, str] = {
    "Acre": "AC",
    "Alagoas": "AL",
    "Amapá": "AP",
    "Amazonas": "AM",
    "Bahia": "BA",
    "Ceará": "CE",
    "Distrito Federal": "DF",
    "Espírito Santo": "ES",
    "Goiás": "GO",
    "Maranhão": "MA",
    "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG",
    "Pará": "PA",
    "Paraíba": "PB",
    "Paraná": "PR",
    "Pernambuco": "PE",
    "Piauí": "PI",
    "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS",
    "Rondônia": "RO",
    "Roraima": "RR",
    "Santa Catarina": "SC",
    "São Paulo": "SP",
    "Sergipe": "SE",
    "Tocantins": "TO",
    # Common abbreviation variants seen in files
    "Mato G. do Sul": "MS",
    "Mato G. Sul": "MS",
    "Rio G. do Sul": "RS",
    "Rio G. Sul": "RS",
    "Rio G. do Norte": "RN",
    "Espírito  Santo": "ES",  # double space variant
}

# Reverse map for lookups
STATE_CODE_TO_NAME: dict[str, str] = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}

# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; conab-crop-progress-bot/0.1; "
        "+https://github.com/conab-crop-progress)"
    ),
}
REQUEST_DELAY_SECONDS = 1.5
REQUEST_TIMEOUT = 60
