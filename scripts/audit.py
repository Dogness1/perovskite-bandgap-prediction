#!/usr/bin/env python3
"""导师方案第0步：标签质量审计，输出 JSON + 待回查清单 CSV。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT, load_config  # noqa: E402
from src.data.loader import load_pairs  # noqa: E402
from src.data.preprocessor import extract_features  # noqa: E402
from src.data.cleaner import audit_labels  # noqa: E402


def main():
    import argparse
    ap = argparse.ArgumentParser(description="标签质量审计")
    ap.add_argument("--config", default="base.json")
    args = ap.parse_args()
    cfg = load_config(args.config)
    pairs = load_pairs(cfg)
    df = extract_features(pairs["df"])
    result = audit_labels(df)
    out = ROOT / "experiments" / "results" / "v3_label_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"3σ候选={result['outlier_count']} τ异常={result['tau_anomaly_count']} "
          f"B位层={len(result['by_B_site'])} -> {out}")
    if result["outlier_3sigma_candidates"]:
        import pandas as pd
        pd.DataFrame(result["outlier_3sigma_candidates"]).to_csv(
            ROOT / "experiments" / "pending_review.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
