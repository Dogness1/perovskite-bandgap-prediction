#!/usr/bin/env python3
"""导师方案第3步：生成主动学习 DFT 计算队列。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT, load_config  # noqa: E402
from src.data.dataset import build_dataset  # noqa: E402
from src.active.candidate import build_queue  # noqa: E402


def main():
    import argparse
    ap = argparse.ArgumentParser(description="主动学习队列")
    ap.add_argument("--config", default="base.json")
    ap.add_argument("--n", type=int, default=2000)
    args = ap.parse_args()
    cfg = load_config(args.config)
    data = build_dataset(cfg)
    summary = build_queue(data, cfg, ROOT / "experiments" / "active_learning_queue.csv",
                          n_candidates=args.n)
    out = ROOT / "experiments" / "results" / "v3_active_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"候选={summary['n_selected']} 窗口内={summary['n_in_target_window']} -> {out}")


if __name__ == "__main__":
    main()
