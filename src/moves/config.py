from __future__ import annotations

from datetime import date
from types import MappingProxyType

AS_OF_DATE = date(2026, 10, 31)
DISPATCH_DATE = date(2026, 11, 1)
WH_LOCATION = "WH-KOL"

DONOR_SURPLUS_DAYS = 45
DONOR_SAFETY_DAYS = 30
APPROVAL_THRESHOLD_MRP = 100_000

# Day values mirror data/csv/lead_times.csv until a shared config exists (D-12).
W2S_DAYS_BY_ZONE = MappingProxyType({"East": 3, "North": 4, "South": 6})
S2S_SAME_CITY_DAYS = 2
S2S_SAME_ZONE_DAYS = 4
S2S_CROSS_ZONE_DAYS = 7

ACCESSORIES_CATEGORY = "Accessories (Safa/Mala/Stole)"
CATEGORY_MAP = MappingProxyType(
    {c: ACCESSORIES_CATEGORY for c in ("Safa", "Mala", "Stole")}
)


def display_category(category: str) -> str:
    return CATEGORY_MAP.get(category, category)
