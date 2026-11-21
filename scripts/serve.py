#!/usr/bin/env python3
"""启动 v3 API 服务：python scripts/serve.py。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.api.app import app, get_service  # noqa: E402

if __name__ == "__main__":
    get_service()
    app.run(host="0.0.0.0", port=5000, debug=True)
