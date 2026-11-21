"""Detection of stockout, ageing, and zero-sales findings."""
from typing import Tuple

from src.velocity_cover.models import Finding, FindingType, InventoryPosition
from src.velocity_cover.repositories import VelocityCoverRepository


class ProblemDetectionService:
    def __init__(self, repository: VelocityCoverRepository):
        self.repository = repository

    def detect(self, positions: Tuple[InventoryPosition, ...], sku_velocities: Tuple) -> Tuple[Finding, ...]:
        findings = []
        velocity_by_key = {
            (row.store_id, row.sku_id): row for row in sku_velocities
        }

        for position in positions:
            item = self.repository.items.get_by_id(position.sku_id)
            if not item:
                continue

            lead_time = self.repository.rules.get_lead_time_days("WH-KOL", position.store_id)
            if position.cover_days < lead_time:
                potential_loss = position.daily_velocity * item.mrp
                findings.append(
                    Finding(
                        finding_type=FindingType.STOCKOUT_RISK,
                        store_id=position.store_id,
                        sku_id=position.sku_id,
                        style_id=item.style_id,
                        metric_value=position.cover_days,
                        diagnosis=f"Cover is below the {lead_time}-day inbound lead time",
                        potential_revenue_loss=potential_loss,
                    )
                )

            if not item.is_core_style and position.stock_age_days > 90 and position.cover_days > 60:
                findings.append(
                    Finding(
                        finding_type=FindingType.AGEING_RISK,
                        store_id=position.store_id,
                        sku_id=position.sku_id,
                        style_id=item.style_id,
                        metric_value=position.stock_age_days,
                        diagnosis=f"Fashion SKU is {position.stock_age_days} days old with {position.cover_days:.1f} days cover",
                    )
                )

        for key in sorted(velocity_by_key):
            store_id, sku_id = key
            velocity = velocity_by_key[key]
            if velocity.quantity_sold != 0:
                continue
            item = self.repository.items.get_by_id(sku_id)
            if not item:
                continue
            reason = "no stock" if velocity.days_in_stock == 0 else "no demand"
            findings.append(
                Finding(
                    finding_type=FindingType.ZERO_SALES_DIAGNOSIS,
                    store_id=store_id,
                    sku_id=sku_id,
                    style_id=item.style_id,
                    metric_value=float(velocity.days_in_stock),
                    diagnosis=reason,
                )
            )

        stockout = [
            finding
            for finding in findings
            if finding.finding_type == FindingType.STOCKOUT_RISK
        ]
        stockout.sort(
            key=lambda finding: (
                -finding.potential_revenue_loss,
                finding.store_id,
                finding.sku_id or "",
            )
        )
        non_stockout = [
            finding
            for finding in findings
            if finding.finding_type != FindingType.STOCKOUT_RISK
        ]
        return tuple(stockout + sorted(
            non_stockout,
            key=lambda finding: (
                finding.finding_type.value,
                finding.store_id,
                finding.sku_id or "",
            ),
        ))
