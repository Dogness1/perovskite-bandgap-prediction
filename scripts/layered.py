#!/usr/bin/env python3
"""B 位分层 Δ 模型实验（导师方案第1步分层 / B 位物理分层）。

覆盖全量 281（Ca/Ba/Sr/Sn/Ge/Pb 六种），小样本层全量回代（乐观估计，明确标注）。
新实验线，不与全局 C1 基线直接对比（宪法 3.1/3.4）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.model_selection import KFold

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT, load_config  # noqa: E402
from src.data.dataset import build_dataset  # noqa: E402
from src.models.layered import layered_fit_predict  # noqa: E402
from src.evaluation.metrics import compute_metrics  # noqa: E402


def main():
    import argparse
    ap = argparse.ArgumentParser(description="B位分层Δ模型实验")
    ap.add_argument("--config", default="base.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cfg = load_config(args.config)
    data = build_dataset(cfg)
    n_est = 10 if args.dry_run else cfg["model"]["n_estimators"]
    cfg_run = dict(cfg)
    pred = layered_fit_predict(
        data["X_pair"], data["delta"], data["b_site"], cfg_run,
        KFold, n_estimators=n_est)["pred"]
    metrics = compute_metrics(data["y_hse"], data["y_pbe_pair"] + pred)
    record = dict(
        experiment_id="v3-layered-B",
        config_hash="layered-" + cfg.get("experiment_id", "base"),
        metrics=metrics,
        coverage=1.0,
        note="6 位分层，小样本层全量回代（乐观）；新实验线，不与 C1 全局口径直接对比",
        dry=args.dry_run,
    )
    out = ROOT / "experiments" / "results" / "v3_layered_B.json"
    if args.dry_run:
        out = out.with_name("v3_layered_B_dry.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"layered-B R²={metrics['r2']:.4f} MAE={metrics['mae']:.4f} "
          f"n={metrics['n']} -> {out}")


if __name__ == "__main__":
    main()
