"""Bridge adapter converting Track 1 and Track 2 models into Track 3's EngineInputs."""
from collections import defaultdict
from typing import Dict, FrozenSet, Mapping, Optional, Set, Tuple

from src.domain.models import Item as DomainItem
from src.domain.models import Store as DomainStore
from src.infrastructure.in_memory_repository import InMemoryRepositoryContainer
from src.moves.config import WH_LOCATION, display_category
from src.moves.inputs import EngineInputs, Item, Position, Store
from src.velocity_cover.models import VelocityCoverResult


def build_engine_inputs(
    repo: InMemoryRepositoryContainer,
    vc: VelocityCoverResult,
) -> EngineInputs:
    """Build immutable EngineInputs from Track 1 repository and Track 2 velocity/cover results."""
    # 1. Stores
    raw_stores = repo.stores.get_all()
    stores: Tuple[Store, ...] = tuple(
        Store(
            store_id=s.store_id,
            city=s.city,
            zone=s.zone,
            tier=s.tier,
            stock_capacity_units=s.stock_capacity_units,
        )
        for s in raw_stores
    )

    # 2. Items
    raw_items = repo.items.get_all()
    items: Tuple[Item, ...] = tuple(
        Item(
            sku_id=i.sku_id,
            style_id=i.style_id,
            category=i.category,
            mrp=int(round(i.mrp)),
        )
        for i in raw_items
    )
    items_by_sku: Dict[str, DomainItem] = {i.sku_id: i for i in raw_items}

    # 3. Positions (locations: 20 stores + WH-KOL)
    all_locations = [s.store_id for s in raw_stores] + [WH_LOCATION]
    positions_list = []
    style_effective_stock: Dict[Tuple[str, str], int] = defaultdict(int)

    for loc in all_locations:
        for item in raw_items:
            pos = repo.stock.get_position(loc, item.sku_id)
            if pos:
                on_hand = pos.on_hand
                in_transit = pos.in_transit
                quarantined = pos.is_untrusted
            else:
                on_hand = 0
                in_transit = 0
                quarantined = False

            positions_list.append(
                Position(
                    location_id=loc,
                    sku_id=item.sku_id,
                    on_hand=on_hand,
                    in_transit=in_transit,
                    quarantined=quarantined,
                )
            )

            # Tally style effective stock for stores (excluding quarantined and warehouse)
            if loc != WH_LOCATION and not quarantined:
                eff = on_hand + in_transit
                style_effective_stock[(loc, item.style_id)] += max(0, eff)

    positions: Tuple[Position, ...] = tuple(positions_list)

    # 4. Velocities
    sku_velocity: Dict[Tuple[str, str], float] = {
        (v.store_id, v.sku_id): v.velocity for v in vc.sku_velocities
    }

    style_velocity: Dict[Tuple[str, str], float] = {
        (v.store_id, v.level_id): v.velocity
        for v in vc.style_velocities
        if v.level == "style"
    }

    # 5. Style cover: effective style stock / style velocity (None if vel <= 0)
    style_cover: Dict[Tuple[str, str], Optional[float]] = {}
    for (st_id, sty_id), vel in style_velocity.items():
        if vel > 0:
            eff_stock = style_effective_stock.get((st_id, sty_id), 0)
            style_cover[(st_id, sty_id)] = eff_stock / vel
        else:
            style_cover[(st_id, sty_id)] = None

    # 6. Min display (24 rows)
    min_display: Dict[Tuple[str, str], int] = {}
    tiers = ("S++", "S+", "A", "B")
    categories = ("Kurta Set", "Sherwani", "Indo-Western", "Jacket", "Mojari", "Accessories (Safa/Mala/Stole)")
    for tier in tiers:
        for cat in categories:
            min_display[(tier, cat)] = repo.rules.get_min_display(tier, cat)

    # 7. Flagship protected frozenset ((store_id, style_id))
    flagship_pairs: Set[Tuple[str, str]] = set()
    for s in raw_stores:
        if s.tier == "S++":
            for style_id in repo.rules.get_flagship_protected_styles(s.store_id):
                flagship_pairs.add((s.store_id, style_id))
    flagship = frozenset(flagship_pairs)

    # 8. Warehouse velocity rollup (sum of sku velocity across all stores)
    wh_velocity: Dict[str, float] = defaultdict(float)
    for (st_id, sku_id), vel in sku_velocity.items():
        wh_velocity[sku_id] += vel

    return EngineInputs(
        stores=stores,
        items=items,
        positions=positions,
        sku_velocity=sku_velocity,
        style_velocity=style_velocity,
        style_cover=style_cover,
        min_display=min_display,
        flagship=flagship,
        wh_velocity=wh_velocity,
    )
