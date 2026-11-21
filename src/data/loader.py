"""数据加载与配对校验（导师方案第0步前置）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

from src.config import ROOT


def load_pairs(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """读取 PBE/HSErel_SOC 两表并按 Formula 一一配对，输出 Δ 标签与分组。

    in : cfg(dict) 含 data.path / sheet_pbe / sheet_hse / key / target
    out: dict{ df(DataFrame), pbe, hse, delta, groups(A_B), b_site, n }
    """
    path = ROOT / cfg["data"]["path"]
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在: {path}")
    d = cfg["data"]
    pbe = pd.read_excel(path, sheet_name=d["sheet_pbe"])
    hse = pd.read_excel(path, sheet_name=d["sheet_hse"])
    key, tgt = d["key"], d["hse_target"]
    if not pbe[key].is_unique or not hse[key].is_unique:
        raise ValueError("Formula 不唯一，Δ 配对不可靠")
    hmap = hse.set_index(key)[tgt]
    mask = pbe[key].isin(hmap.index).to_numpy()
    paired = pbe.loc[mask].reset_index(drop=True).copy()
    paired["hse_gap"] = hmap.reindex(paired[key]).to_numpy(float)
    paired["pbe_gap"] = paired[d["pbe_target"]].to_numpy(float)
    paired["delta"] = paired["hse_gap"] - paired["pbe_gap"]
    return dict(
        df=paired,
        pbe=paired["pbe_gap"].to_numpy(float),
        hse=paired["hse_gap"].to_numpy(float),
        delta=paired["delta"].to_numpy(float),
        n=len(paired),
        formulas=paired[key].tolist(),
    )
