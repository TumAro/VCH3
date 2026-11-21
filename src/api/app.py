"""FastAPI app: HTTP mapping only. Business logic lives in services / DataContext."""
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.data_context import DataContext

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
