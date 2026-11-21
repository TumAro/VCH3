"""Single-entry launcher for Manyavar Daily Stock Move Recommender."""
import argparse
import os
from pathlib import Path
import sys
import webbrowser

import uvicorn

from src.cli import run_pipeline


def main():
    default_port = int(os.environ.get("PORT", 8000))
    default_host = os.environ.get("HOST", "127.0.0.1")

    parser = argparse.ArgumentParser(description="Manyavar Daily Stock Move Recommender")
    parser.add_argument("--cli", action="store_true", help="Run headless CLI pipeline and exit")
    parser.add_argument("--host", default=default_host, help=f"Server host (default: {default_host})")
    parser.add_argument("--port", type=int, default=default_port, help=f"Server port (default: {default_port})")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    parser.add_argument("--data-dir", type=Path, default=Path("data/csv"), help="Path to data directory")
    args = parser.parse_args()

    if args.cli:
        sys.exit(run_pipeline(args.data_dir, Path(".")))

    url = f"http://{args.host}:{args.port}"
    print("=" * 60)
    print("  Manyavar Daily Stock Move Recommender")
    print(f"  Web Dashboard: {url}")
    print("=" * 60)

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    from src.api.app import create_app
    app = create_app(args.data_dir)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
