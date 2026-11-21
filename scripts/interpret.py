#!/usr/bin/env python3
"""导师方案解释层：SHAP 对 Δ 模型做事后解释。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT, load_config  # noqa: E402
from src.data.dataset import build_dataset  # noqa: E402
from src.interpretation.shap_analysis import explain_delta  # noqa: E402


def main():
    import argparse
    ap = argparse.ArgumentParser(description="SHAP 解释")
    ap.add_argument("--config", default="base.json")
    args = ap.parse_args()
    cfg = load_config(args.config)
    data = build_dataset(cfg)
    result = explain_delta(data["X_pair"], data["delta"], data["names"], cfg)
    out = ROOT / "experiments" / "results" / "v3_shap.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SHAP Top3:", [r["feature"] for r in result["top_features"][:3]], f"-> {out}")


if __name__ == "__main__":
    main()
