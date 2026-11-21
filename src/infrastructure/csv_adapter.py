"""CSV data source adapter loading Manyavar retail tables."""
import csv
from datetime import date, datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.domain.models import (
    DataIssue,
    FlagshipProtectedRule,
    Item,
    LeadTimeRule,
    MinDisplayRule,
    SalesLine,
    StockPosition,
    Store,
    WarehouseInbound,
    WeeklyStock,
)

logger = logging.getLogger(__name__)


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse YYYY-MM-DD string to date object, or return None if empty."""
    if not date_str or not date_str.strip():
        return None
    return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()


class CSVDataSourceAdapter:
    """Reads and sanitizes CSV data from data/csv/."""

    AS_OF_DATE = date(2026, 10, 31)

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_issues: List[DataIssue] = []

    def load_stores(self) -> List[Store]:
        path = self.data_dir / "stores.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")

        stores = []
        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                store_id = str(row["store_id"]).strip()
                opened_on = parse_date(row["opened_on"])
                if not opened_on:
                    opened_on = self.AS_OF_DATE
                is_new = (self.AS_OF_DATE - opened_on).days < 28

                stores.append(
                    Store(
                        store_id=store_id,
                        city=str(row["city"]).strip(),
                        state=str(row["state"]).strip(),
                        zone=str(row["zone"]).strip(),
                        tier=str(row["tier"]).strip(),
                        size_sqft=int(row["size_sqft"]),
                        stock_capacity_units=int(row["stock_capacity_units"]),
                        opened_on=opened_on,
                        area_manager_id=str(row["area_manager_id"]).strip(),
                        is_new_store=is_new,
                    )
                )
        return stores

    def load_items(self) -> List[Item]:
        path = self.data_dir / "items.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")

        items = []
        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                is_pkg = int(row.get("is_packaging", 0)) == 1 or row["sku_id"].strip().startswith("PKG-")
                if is_pkg:
                    continue  # Strip packaging SKUs

                items.append(
                    Item(
                        sku_id=str(row["sku_id"]).strip(),
                        style_id=str(row["style_id"]).strip(),
                        style_name=str(row["style_name"]).strip(),
                        category=str(row["category"]).strip(),
                        size=str(row["size"]).strip(),
                        mrp=float(row["mrp"]),
                        cost_price=float(row["cost_price"]),
                        launch_date=parse_date(row.get("launch_date")),
                        is_core_style=int(row.get("is_core_style", 0)) == 1,
                        is_packaging=False,
                    )
                )
        return items

    def load_weekly_stock(self, valid_sku_ids: Set[str]) -> List[WeeklyStock]:
        path = self.data_dir / "stock_weekly.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")

        weekly_stocks = []
        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku_id = str(row["sku_id"]).strip()
                if sku_id not in valid_sku_ids:
                    continue  # skip packaging or unknown SKUs

                weekly_stocks.append(
                    WeeklyStock(
                        week_ending=parse_date(row["week_ending"]) or self.AS_OF_DATE,
                        store_id=str(row["store_id"]).strip(),
                        sku_id=sku_id,
                        closing_on_hand=int(row["closing_on_hand"]),
                        days_in_stock=int(row["days_in_stock"]),
                    )
                )
        return weekly_stocks

    def load_stock_snapshot(
        self,
        valid_sku_ids: Set[str],
        store_capacities: Dict[str, int],
        final_week_stock: Dict[Tuple[str, str], int],
    ) -> List[StockPosition]:
        path = self.data_dir / "stock_snapshot.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")

        positions = []
        store_on_hand_sums: Dict[str, int] = {}

        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku_id = str(row["sku_id"]).strip()
                if sku_id not in valid_sku_ids:
                    continue

                location_id = str(row["location_id"]).strip()
                on_hand = int(row["on_hand"])
                in_transit = int(row.get("in_transit") or 0)
                in_transit_arrives = parse_date(row.get("in_transit_arrives_on"))
                oldest_stock_date = parse_date(row.get("oldest_stock_received_on"))

                is_untrusted = False
                untrusted_reason = None

                # Check 1: Negative on-hand
                if on_hand < 0:
                    is_untrusted = True
                    untrusted_reason = "Negative on-hand stock"
                    self.data_issues.append(
                        DataIssue(
                            table="stock_snapshot",
                            key=f"{location_id}/{sku_id}",
                            column="on_hand",
                            value_seen=str(on_hand),
                            rule_violated="on_hand >= 0",
                            action_taken="Marked untrusted and quarantined from move proposals",
                        )
                    )

                # Check 2: Mismatch with weekly closing stock at 2026-10-31
                if location_id != "WH-KOL":
                    weekly_closing = final_week_stock.get((location_id, sku_id))
                    if weekly_closing is not None and weekly_closing != on_hand:
                        is_untrusted = True
                        untrusted_reason = f"Snapshot ({on_hand}) disagrees with weekly closing ({weekly_closing})"
                        self.data_issues.append(
                            DataIssue(
                                table="stock_snapshot",
                                key=f"{location_id}/{sku_id}",
                                column="on_hand",
                                value_seen=f"Snapshot {on_hand} vs Weekly {weekly_closing}",
                                rule_violated="snapshot on_hand == final weekly closing",
                                action_taken="Marked untrusted and quarantined from move proposals",
                            )
                        )

                store_on_hand_sums[location_id] = store_on_hand_sums.get(location_id, 0) + on_hand

                positions.append(
                    StockPosition(
                        location_id=location_id,
                        sku_id=sku_id,
                        on_hand=on_hand,
                        in_transit=in_transit,
                        in_transit_arrives_on=in_transit_arrives,
                        oldest_stock_received_on=oldest_stock_date,
                        is_untrusted=is_untrusted,
                        untrusted_reason=untrusted_reason,
                    )
                )

        # Check 3: Store total stock capacity breaches
        for store_id, total_on_hand in store_on_hand_sums.items():
            if store_id in store_capacities:
                cap = store_capacities[store_id]
                if total_on_hand > cap:
                    self.data_issues.append(
                        DataIssue(
                            table="stores",
                            key=store_id,
                            column="stock_capacity_units",
                            value_seen=f"Total stock {total_on_hand} > capacity {cap}",
                            rule_violated="store total on_hand <= capacity",
                            action_taken="Flagged store capacity overage",
                        )
                    )

        return positions

    def load_warehouse_inbound(self, valid_sku_ids: Set[str]) -> List[WarehouseInbound]:
        path = self.data_dir / "warehouse_inbound.csv"
        if not path.exists():
            return []

        inbounds = []
        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku_id = str(row["sku_id"]).strip()
                if sku_id not in valid_sku_ids:
                    continue

                inbounds.append(
                    WarehouseInbound(
                        expected_date=parse_date(row["expected_date"]) or self.AS_OF_DATE,
                        sku_id=sku_id,
                        qty=int(row["qty"]),
                        status=str(row["status"]).strip(),
                    )
                )
        return inbounds

    def load_sales_lines(self, valid_sku_ids: Set[str]) -> List[SalesLine]:
        bills_path = self.data_dir / "bills.csv"
        lines_path = self.data_dir / "bill_lines.csv"
        if not bills_path.exists() or not lines_path.exists():
            raise FileNotFoundError("Missing bills or bill_lines CSV")

        # Map bills: bill_id -> (bill_date, store_id, salesperson_id, customer_id)
        bills_map: Dict[str, Tuple[date, str, str, str]] = {}
        with open(bills_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                b_date = parse_date(row["bill_date"]) or self.AS_OF_DATE
                bills_map[str(row["bill_id"]).strip()] = (
                    b_date,
                    str(row["store_id"]).strip(),
                    str(row["salesperson_id"]).strip(),
                    str(row["customer_id"]).strip(),
                )

        sales_lines = []
        with open(lines_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku_id = str(row["sku_id"]).strip()
                if sku_id not in valid_sku_ids:
                    continue  # Strip packaging items

                bill_id = str(row["bill_id"]).strip()
                bill_meta = bills_map.get(bill_id)
                if not bill_meta:
                    continue

                b_date, store_id, sp_id, cust_id = bill_meta
                sales_lines.append(
                    SalesLine(
                        bill_id=bill_id,
                        bill_date=b_date,
                        store_id=store_id,
                        salesperson_id=sp_id,
                        customer_id=cust_id,
                        sku_id=sku_id,
                        qty=int(row["qty"]),
                        mrp=float(row["mrp"]),
                        selling_price=float(row["selling_price"]),
                    )
                )
        return sales_lines

    def load_min_display(self) -> Dict[Tuple[str, str], int]:
        path = self.data_dir / "min_display.csv"
        if not path.exists():
            return {}

        rules: Dict[Tuple[str, str], int] = {}
        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tier = str(row["tier"]).strip()
                cat = str(row["category"]).strip()
                qty = int(row["min_display_units"])
                rules[(tier, cat)] = qty
        return rules

    def load_flagship_protected(self) -> Dict[str, Set[str]]:
        path = self.data_dir / "flagship_protected.csv"
        if not path.exists():
            return {}

        protected: Dict[str, Set[str]] = {}
        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                store_id = str(row["store_id"]).strip()
                style_id = str(row["style_id"]).strip()
                if store_id not in protected:
                    protected[store_id] = set()
                protected[store_id].add(style_id)
        return protected

    def load_lead_times(self) -> List[LeadTimeRule]:
        path = self.data_dir / "lead_times.csv"
        if not path.exists():
            return []

        lead_times = []
        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                lead_times.append(
                    LeadTimeRule(
                        route=str(row["route"]).strip(),
                        days=int(row["days"]),
                    )
                )
        return lead_times
