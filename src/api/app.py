"""FastAPI app: HTTP mapping only. Business logic lives in services / DataContext."""
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import Body, FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.data_context import DataContext
from src.services.export_service import ExportService

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def create_app(data_dir: Path, context: Optional[DataContext] = None) -> FastAPI:
    ctx = context or DataContext(Path(data_dir))
    app = FastAPI(title="Daily Stock Move Recommender")

    @app.get("/api/status")
    def status():
        return {"last_run": ctx.current().last_run.isoformat(timespec="seconds")}

    @app.get("/api/revenue/monthly")
    def monthly_revenue():
        monthly = ctx.current().monthly
        return {
            "months": monthly.months,
            "series": [{"state": state, "values": values} for state, values in monthly.series.items()],
        }

    @app.get("/api/network")
    def network():
        return asdict(ctx.current().overview)

    @app.get("/api/notifications")
    def notifications():
        return {"items": [asdict(n) for n in ctx.current().notifications]}

    @app.get("/api/moves")
    def list_moves(
        move_type: Optional[str] = Query(None),
        store_id: Optional[str] = Query(None),
        category: Optional[str] = Query(None),
        decision: Optional[str] = Query(None),
        search: Optional[str] = Query(None),
        requires_approval: Optional[bool] = Query(None),
    ):
        moves = ctx.get_filtered_moves(
            move_type=move_type,
            store_id=store_id,
            category=category,
            decision=decision,
            search=search,
            requires_approval=requires_approval,
        )
        return {"items": moves, "count": len(moves)}

    @app.post("/api/moves/{move_id}/decision")
    def set_move_decision(move_id: int, payload: dict = Body(...)):
        decision = payload.get("decision", "Waiting")
        if decision not in ("Approved", "Rejected", "Waiting"):
            raise HTTPException(status_code=400, detail="Decision must be Approved, Rejected, or Waiting")

        success = ctx.set_decision(move_id, decision)
        if not success:
            raise HTTPException(status_code=404, detail=f"Move {move_id} not found")

        return {"status": "ok", "id": move_id, "decision": decision}

    @app.get("/api/moves/summary")
    def moves_summary():
        return asdict(ctx.current().summary)

    @app.get("/api/findings")
    def list_findings(finding_type: Optional[str] = Query(None)):
        findings = ctx.current().findings
        if finding_type:
            findings = [f for f in findings if (f.finding_type.value if hasattr(f.finding_type, "value") else str(f.finding_type)).lower() == finding_type.lower()]
        return {"items": [asdict(f) for f in findings], "count": len(findings)}

    @app.get("/api/export/csv")
    def export_csv():
        approved_moves = ctx.get_approved_moves_for_export()
        csv_str = ExportService.generate_csv_string(approved_moves)
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=moves.csv"},
        )

    @app.get("/api/export/xlsx")
    def export_xlsx():
        approved_moves = ctx.get_approved_moves_for_export()
        data = ctx.current()
        xlsx_bytes = ExportService.generate_excel_bytes(
            moves=approved_moves,
            findings=data.findings,
            rejected=data.rejected_moves,
        )
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=moves.xlsx"},
        )

    @app.post("/api/sync")
    def sync():
        try:
            loaded = ctx.rerun()
        except Exception as exc:  # any load failure: keep last good data, report the error
            return JSONResponse(status_code=500, content={"status": "error", "message": str(exc)})
        return {"status": "ok", "last_run": loaded.last_run.isoformat(timespec="seconds")}

    @app.get("/")
    def index():
        return FileResponse(WEB_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=WEB_DIR, check_dir=False), name="static")
    return app
