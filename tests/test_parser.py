"""Tests for the CONAB crop progress parser."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

from conab_crop_progress.parser import _coerce_pct, parse_directory, parse_file
from conab_crop_progress.translator import (
    normalize_activity,
    normalize_crop,
    normalize_state,
)

# ---------------------------------------------------------------------------
# Unit tests: value coercion
# ---------------------------------------------------------------------------


class TestCoercePct:
    """CONAB values are always on a 0-100 scale; we normalise to 0-1."""

    def test_float_half_percent(self):
        # 0.5 in CONAB means 0.5% → 0.005
        assert _coerce_pct(0.5) == pytest.approx(0.005)

    def test_float_50_percent(self):
        assert _coerce_pct(50.0) == pytest.approx(0.5)

    def test_int_100(self):
        assert _coerce_pct(100) == pytest.approx(1.0)

    def test_int_0(self):
        assert _coerce_pct(0) == 0.0

    def test_string_comma_decimal(self):
        assert _coerce_pct("0,5") == pytest.approx(0.005)

    def test_string_with_pct_sign(self):
        assert _coerce_pct("50%") == pytest.approx(0.5)

    def test_string_with_asterisks(self):
        assert _coerce_pct("0,5% **") == pytest.approx(0.005)

    def test_none(self):
        assert _coerce_pct(None) is None

    def test_dash(self):
        assert _coerce_pct("-") is None

    def test_empty_string(self):
        assert _coerce_pct("") is None

    def test_string_100(self):
        assert _coerce_pct("100") == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Unit tests: translator
# ---------------------------------------------------------------------------


class TestNormalizeCrop:
    def test_basic_crops(self):
        assert normalize_crop("Soja") == "soybeans"
        assert normalize_crop("Milho 1ª") == "corn_1"
        assert normalize_crop("Milho 2ª") == "corn_2"
        assert normalize_crop("Algodão") == "cotton"
        assert normalize_crop("Arroz") == "rice"
        assert normalize_crop("Trigo") == "wheat"

    def test_feijao_variants(self):
        assert normalize_crop("Feijão 1ª") == "dry_beans_1"
        assert normalize_crop("Feijão 2ª") == "dry_beans_2"
        assert normalize_crop("Feijão 3ª") == "dry_beans_3"

    def test_whitespace(self):
        assert normalize_crop("  Soja  ") == "soybeans"
        assert normalize_crop("Milho  1ª") == "corn_1"

    def test_unknown(self):
        assert normalize_crop("Banana") is None


class TestNormalizeActivity:
    def test_semeadura(self):
        assert normalize_activity("Semeadura") == "planting"

    def test_colheita(self):
        assert normalize_activity("Colheita") == "harvest"

    def test_colheita_asterisk(self):
        assert normalize_activity("Colheita *") == "harvest"
        assert normalize_activity("Colheita*") == "harvest"

    def test_unknown(self):
        assert normalize_activity("Transporte") is None


class TestNormalizeState:
    def test_basic_states(self):
        assert normalize_state("Mato Grosso") == "MT"
        assert normalize_state("São Paulo") == "SP"
        assert normalize_state("Paraná") == "PR"
        assert normalize_state("Goiás") == "GO"
        assert normalize_state("Rio Grande do Sul") == "RS"

    def test_abbreviation_variants(self):
        assert normalize_state("Mato G. do Sul") == "MS"

    def test_whitespace(self):
        assert normalize_state("  Mato Grosso  ") == "MT"

    def test_unknown(self):
        assert normalize_state("Atlantis") is None


# ---------------------------------------------------------------------------
# Integration: parse real files if available
# ---------------------------------------------------------------------------

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"


def _find_sample_xlsx() -> list[Path]:
    """Find crop progress xlsx files in the raw data directory."""
    if not RAW_DIR.exists():
        return []
    # Only pick "Plantio" files (crop progress), not "Fenologia" etc.
    return sorted(
        p for p in RAW_DIR.rglob("*.xlsx")
        if "plantio" in p.name.lower() or "Plantio" in p.name
    )[:3]


@pytest.mark.skipif(
    not _find_sample_xlsx(),
    reason="No sample xlsx files found in data/raw/",
)
class TestParseRealFiles:
    """Integration tests that run against actual downloaded files."""

    def test_parse_file_returns_records(self):
        sample = _find_sample_xlsx()[0]
        records = parse_file(sample)
        assert len(records) > 0, f"No records parsed from {sample.name}"

    def test_record_schema(self):
        sample = _find_sample_xlsx()[0]
        records = parse_file(sample)
        required_keys = {
            "report_date", "week_start", "week_end",
            "crop", "crop_season", "activity",
            "state", "state_code", "is_total",
            "progress_pct", "prev_week_pct", "prev_year_pct",
            "five_year_avg_pct", "source_file",
        }
        for rec in records[:5]:
            assert required_keys <= set(rec.keys()), (
                f"Missing keys: {required_keys - set(rec.keys())}"
            )

    def test_valid_crops(self):
        sample = _find_sample_xlsx()[0]
        records = parse_file(sample)
        valid_crops = {
            "cotton", "rice", "dry_beans_1", "dry_beans_2",
            "dry_beans_3", "corn_1", "corn_2", "soybeans", "wheat",
        }
        for rec in records:
            assert rec["crop"] in valid_crops, f"Invalid crop: {rec['crop']}"

    def test_valid_activities(self):
        sample = _find_sample_xlsx()[0]
        records = parse_file(sample)
        for rec in records:
            assert rec["activity"] in ("planting", "harvest"), (
                f"Invalid activity: {rec['activity']}"
            )

    def test_progress_range(self):
        """Progress values should be in [0, 1] when not None."""
        sample = _find_sample_xlsx()[0]
        records = parse_file(sample)
        for rec in records:
            for col in ("progress_pct", "prev_week_pct", "prev_year_pct"):
                val = rec[col]
                if val is not None:
                    assert 0.0 <= val <= 1.0, (
                        f"{col}={val} out of range for "
                        f"{rec['state']}/{rec['crop']}"
                    )

    def test_state_codes(self):
        """Non-total rows should have valid 2-letter state codes."""
        sample = _find_sample_xlsx()[0]
        records = parse_file(sample)
        for rec in records:
            if not rec["is_total"]:
                assert len(rec["state_code"]) == 2, (
                    f"Invalid state code: {rec['state_code']}"
                )
