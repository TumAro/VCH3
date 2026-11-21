"""Effective inventory, cover, and stock-age calculations."""
from datetime import date
from typing import Dict, Tuple

from src.velocity_cover.models import InventoryPosition
from src.velocity_cover.repositories import VelocityCoverRepository


AS_OF_DATE = date(2026, 10, 31)
INFINITE_COVER_DAYS = 999.0


class PositionCoverService:
    def __init__(self, repository: VelocityCoverRepository):
        self.repository = repository

    def compute(self, sku_velocities: Tuple) -> Tuple[InventoryPosition, ...]:
        velocity_by_key: Dict[Tuple[str, str], float] = {
            (row.store_id, row.sku_id): row.velocity for row in sku_velocities
        }
        positions = []

        for snapshot in self.repository.stock.get_snapshot_positions():
            if snapshot.is_untrusted:
                continue
            item = self.repository.items.get_by_id(snapshot.sku_id)
            if not item or item.is_packaging:
                continue

            store = self.repository.stores.get_by_id(snapshot.location_id)
            if not store:
                continue

            on_hand = snapshot.on_hand
            in_transit = snapshot.in_transit
            effective_stock = on_hand + in_transit
            velocity = velocity_by_key.get((snapshot.location_id, snapshot.sku_id), 0.0)

            if velocity > 0:
                cover = effective_stock / velocity
            elif effective_stock > 0:
                cover = INFINITE_COVER_DAYS
            else:
                cover = 0.0

            if snapshot.oldest_stock_received_on:
                age = (AS_OF_DATE - snapshot.oldest_stock_received_on).days
                age = max(age, 0)
            else:
                age = 0

            positions.append(
                InventoryPosition(
                    store_id=snapshot.location_id,
                    sku_id=snapshot.sku_id,
                    on_hand=on_hand,
                    in_transit=in_transit,
                    effective_stock=effective_stock,
                    daily_velocity=velocity,
                    cover_days=cover,
                    stock_age_days=age,
                )
            )

        return tuple(sorted(positions, key=lambda row: (row.store_id, row.sku_id)))
