"""Waitress entry point for the Windows-only local runtime."""
from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from central_comercial import create_app  # noqa: E402
from waitress import serve  # noqa: E402


def main() -> None:
    bind = os.environ.get("CENTRAL_BIND", "127.0.0.1")
    if bind != "127.0.0.1":
        raise SystemExit("The Windows local runner only binds to 127.0.0.1.")
    port = int(os.environ.get("CENTRAL_PORT", "8765"))
    if not 1 <= port <= 65535:
        raise SystemExit("CENTRAL_PORT must be between 1 and 65535.")
    serve(create_app(), host=bind, port=port, threads=4, ident="central-comercial")


if __name__ == "__main__":
    main()
