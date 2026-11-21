#!/usr/bin/env python3
"""生成 v3 四类诊断图（导师方案第2步）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import KFold

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT, load_config  # noqa: E402
from src.data.dataset import build_dataset  # noqa: E402
from src.models.delta import build_estimator, fit_fold  # noqa: E402
from src.evaluation.diagnostics import make_diagnostics  # noqa: E402


def main():
    import argparse
    ap = argparse.ArgumentParser(description="v3 诊断图")
    ap.add_argument("--config", default="base.json")
    args = ap.parse_args()
    cfg = load_config(args.config)
    d = build_dataset(cfg)

    # OOF 预测（随机 KFold）用于诊断
    p = np.zeros(d["n_pair"], float)
    for tr, te in KFold(5, shuffle=True, random_state=cfg["model"]["random_state"]).split(d["X_pair"]):
        dp = fit_fold(d["X_pair"][tr], d["delta"][tr], d["X_pair"][te], cfg)
        p[te] = d["y_pbe_pair"][te] + dp
    y = d["y_hse"]

    est = build_estimator(cfg)
    est.fit(d["X_pair"], d["delta"])
    std = np.std([t.predict(d["X_pair"]) for t in est.estimators_], axis=0) \
        if hasattr(est, "estimators_") else np.zeros(len(y))

    out = ROOT / "experiments" / "figures"
    paths = make_diagnostics(y, p, d["cl_raw"], d["br_raw"], std, out)
    manifest = ROOT / "experiments" / "results" / "v3_figures_manifest.json"
    manifest.write_text(json.dumps(paths, ensure_ascii=False, indent=2), encoding="utf-8")
    print("诊断图:", list(paths.keys()), f"-> {out}")


if __name__ == "__main__":
    main()
