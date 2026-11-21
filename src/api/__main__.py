"""Start the dashboard: python -m src.api  ->  http://localhost:8000"""
from pathlib import Path

import uvicorn

from src.api.app import create_app

if __name__ == "__main__":
    uvicorn.run(create_app(Path("data/csv")), host="127.0.0.1", port=8000)
