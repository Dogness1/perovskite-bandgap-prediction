#!/usr/bin/env python3
"""v3 统一训练入口：config 驱动，dry-run → 正式，产出完整实验记录。"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT, load_config  # noqa: E402
from src.data.dataset import build_dataset  # noqa: E402
from src.evaluation.splitter import run_evaluation  # noqa: E402
from src.evaluation.metrics import judge  # noqa: E402


def make_record(cfg: dict, result: dict) -> dict:
    """按宪法 3.2 组装完整实验记录字段。"""
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip() or "unknown"
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        commit += "+dirty"
    cfg_hash = hashlib.sha256(
        json.dumps({k: cfg[k] for k in ("model", "features", "evaluation")},
                   sort_keys=True, default=str).encode()).hexdigest()[:12]
    judgments = {}
    for view, key in (("random_cv", "random_cv"), ("group_cv", "group_cv"),
                      ("external", "external")):
        if key in result:
            # 验收线对标 oracle_pbe（导师历史口径），end_to_end 另报作部署口径
            judgments[view] = judge(view, result[key]["oracle_pbe"])
    return dict(
        experiment_id=result["experiment_id"],
        timestamp=datetime.now(timezone.utc).isoformat(),
        config_hash=cfg_hash,
        code_commit=commit,
        dataset="perovs_data_final.xlsx (PBE+HSErel_SOC) 281 paired",
        seed=cfg["evaluation"]["random_cv"]["seed"],
        config={k: cfg[k] for k in ("model", "features", "evaluation") if k in cfg},
        metrics={k: result[k] for k in ("random_cv", "group_cv", "external") if k in result},
        acceptance_judgment=judgments,
        conclusion="三套验证结果见 metrics；验收判定按 docs/acceptance.md 上修口径",
        notes="end_to_end为主指标；oracle_pbe仅作Δ-learning上限参考；"
              "external为group-disjoint划组，非独立数据源",
    )


def main():
    ap = argparse.ArgumentParser(description="v3 统一训练入口")
    ap.add_argument("--config", default="base.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    mode = "dry" if args.dry_run else "full"
    print(f"[{mode}] config={args.config} exp={cfg.get('experiment_id','base')}", flush=True)
    data = build_dataset(cfg)
    print(f"  data: pair={data['X_pair'].shape} unpair={data['X_unpair'].shape} d={data['d']}",
          flush=True)

    result = run_evaluation(data, cfg, dry=args.dry_run)
    for key in ("random_cv", "group_cv", "external"):
        if key in result:
            e = result[key]["end_to_end"]
            o = result[key]["oracle_pbe"]
            print(f"  {key:12s} E2E R²={e['r2']:.4f} MAE={e['mae']:.4f} | "
                  f"oracle R²={o['r2']:.4f} MAE={o['mae']:.4f}")

    record = make_record(cfg, result)
    out = Path(args.out) if args.out else ROOT / "experiments" / "results" / f"v3_{cfg.get('experiment_id','base')}.json"
    if args.dry_run:
        out = out.with_name(out.stem + "_dry.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"记录已写入 {out}")


if __name__ == "__main__":
    main()
