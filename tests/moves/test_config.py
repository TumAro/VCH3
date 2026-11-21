from __future__ import annotations

from datetime import date

import pytest

from src.moves import config


def test_scalar_values():
    assert config.AS_OF_DATE == date(2026, 10, 31)
    assert config.DISPATCH_DATE == date(2026, 11, 1)
    assert config.WH_LOCATION == "WH-KOL"
    assert config.DONOR_SURPLUS_DAYS == 45
    assert config.DONOR_SAFETY_DAYS == 30
    assert config.APPROVAL_THRESHOLD_MRP == 100_000
    assert config.S2S_SAME_CITY_DAYS == 2
    assert config.S2S_SAME_ZONE_DAYS == 4
    assert config.S2S_CROSS_ZONE_DAYS == 7
    assert config.ACCESSORIES_CATEGORY == "Accessories (Safa/Mala/Stole)"


def test_mappings():
    assert dict(config.W2S_DAYS_BY_ZONE) == {"East": 3, "North": 4, "South": 6}
    assert dict(config.CATEGORY_MAP) == {
        "Safa": config.ACCESSORIES_CATEGORY,
        "Mala": config.ACCESSORIES_CATEGORY,
        "Stole": config.ACCESSORIES_CATEGORY,
    }


def test_mappings_read_only():
    with pytest.raises(TypeError):
        config.W2S_DAYS_BY_ZONE["East"] = 9
    with pytest.raises(TypeError):
        config.CATEGORY_MAP["Safa"] = "x"


@pytest.mark.parametrize("cat", ["Safa", "Mala", "Stole"])
def test_display_category_mapped(cat):
    assert config.display_category(cat) == "Accessories (Safa/Mala/Stole)"


def test_display_category_unchanged():
    assert config.display_category("Kurta Set") == "Kurta Set"
