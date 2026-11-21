"""Single-entry launcher for Manyavar Daily Stock Move Recommender."""
import argparse
from pathlib import Path
import sys
import webbrowser

import uvicorn

from src.cli import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="Manyavar Daily Stock Move Recommender")
    parser.add_argument("--cli", action="store_true", help="Run headless CLI pipeline and exit")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
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
