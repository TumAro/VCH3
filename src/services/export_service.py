"""Export service generating moves.csv and multi-tab moves.xlsx."""
import csv
import io
from pathlib import Path
from typing import List, Sequence

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from src.moves.models import ApprovedMove, RejectedMove
from src.velocity_cover.models import Finding


class ExportService:
    """Produces CSV and multi-tab Excel workbooks for recommended moves and findings."""

    MOVE_HEADERS = [
        "Rank",
        "Type",
        "From",
        "To",
        "SKU",
        "Style",
        "Quantity",
        "MRP Value (INR)",
        "Route Days",
        "Dispatch Date",
        "Arrival Date",
        "Requires Approval",
        "Reason",
    ]

    FINDING_HEADERS = [
        "Finding Type",
        "Store ID",
        "SKU ID",
        "Style ID",
        "Metric Value",
        "Diagnosis",
        "Potential Revenue Loss",
    ]

    REJECTED_HEADERS = [
        "Type",
        "From",
        "To",
        "SKU",
        "Quantity",
        "Rule Violated",
        "Rejection Reason",
    ]

    @classmethod
    def generate_csv_string(cls, moves: Sequence[ApprovedMove]) -> str:
        """Returns CSV string containing approved moves."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(cls.MOVE_HEADERS)

        for rank, m in enumerate(moves, start=1):
            writer.writerow([
                rank,
                m.move_type.value if hasattr(m.move_type, "value") else str(m.move_type),
                m.from_location,
                m.to_location,
                m.sku_id,
                m.style_id,
                m.qty,
                m.value_mrp,
                m.route_days,
                m.dispatch_date.isoformat(),
                m.arrival_date.isoformat(),
                "Yes" if m.requires_human_approval else "No",
                m.reason,
            ])
        return output.getvalue()

    @classmethod
    def generate_excel_bytes(
        cls,
        moves: Sequence[ApprovedMove],
        findings: Sequence[Finding],
        rejected: Sequence[RejectedMove],
    ) -> bytes:
        """Builds an in-memory multi-tab Excel workbook as bytes."""
        wb = openpyxl.Workbook()

        header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        signoff_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")

        # 1. Moves Sheet
        ws_moves = wb.active
        ws_moves.title = "Moves"
        ws_moves.append(cls.MOVE_HEADERS)

        for col_num in range(1, len(cls.MOVE_HEADERS) + 1):
            cell = ws_moves.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        for rank, m in enumerate(moves, start=1):
            m_type = m.move_type.value if hasattr(m.move_type, "value") else str(m.move_type)
            row_data = [
                rank,
                m_type,
                m.from_location,
                m.to_location,
                m.sku_id,
                m.style_id,
                m.qty,
                m.value_mrp,
                m.route_days,
                m.dispatch_date.isoformat(),
                m.arrival_date.isoformat(),
                "Yes" if m.requires_human_approval else "No",
                m.reason,
            ]
            ws_moves.append(row_data)
            row_idx = ws_moves.max_row
            if m.requires_human_approval:
                for col_num in range(1, len(row_data) + 1):
                    ws_moves.cell(row=row_idx, column=col_num).fill = signoff_fill

        # 2. Findings Sheet
        ws_findings = wb.create_sheet(title="Findings")
        ws_findings.append(cls.FINDING_HEADERS)
        for col_num in range(1, len(cls.FINDING_HEADERS) + 1):
            cell = ws_findings.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font

        for f in findings:
            f_type = f.finding_type.value if hasattr(f.finding_type, "value") else str(f.finding_type)
            ws_findings.append([
                f_type,
                f.store_id,
                f.sku_id or "",
                f.style_id or "",
                round(f.metric_value, 2),
                f.diagnosis,
                round(f.potential_revenue_loss, 2),
            ])

        # 3. Rejected Moves Sheet
        ws_rejected = wb.create_sheet(title="Rejected Moves")
        ws_rejected.append(cls.REJECTED_HEADERS)
        for col_num in range(1, len(cls.REJECTED_HEADERS) + 1):
            cell = ws_rejected.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font

        for r in rejected:
            r_type = r.move_type.value if hasattr(r.move_type, "value") else str(r.move_type)
            r_rule = r.rule_violated.value if hasattr(r.rule_violated, "value") else str(r.rule_violated)
            ws_rejected.append([
                r_type,
                r.from_location,
                r.to_location,
                r.sku_id,
                r.qty,
                r_rule,
                r.rejection_reason,
            ])

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    @classmethod
    def write_files_to_dir(
        cls,
        output_dir: Path,
        moves: Sequence[ApprovedMove],
        findings: Sequence[Finding],
        rejected: Sequence[RejectedMove],
    ) -> None:
        """Writes moves.csv and moves.xlsx to output directory."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        csv_content = cls.generate_csv_string(moves)
        with open(out_path / "moves.csv", "w", encoding="utf-8", newline="") as f:
            f.write(csv_content)

        excel_content = cls.generate_excel_bytes(moves, findings, rejected)
        with open(out_path / "moves.xlsx", "wb") as f:
            f.write(excel_content)
