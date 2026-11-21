from __future__ import annotations

from typing import Optional


class ExplanationService:
    def reason(
        self,
        qty: int,
        sku_id: str,
        receiver: str,
        receiver_cover: float,
        velocity: float,
        donor: str,
        donor_cover: Optional[float],
    ) -> str:
        tail = "n/a cover" if donor_cover is None else f"{donor_cover:.1f}d cover"
        return (
            f"Send {int(qty)}: {sku_id} has {receiver_cover:.1f}d cover at {receiver}, "
            f"sells {velocity:.1f}/d; donor {donor} retains {tail}"
        )
