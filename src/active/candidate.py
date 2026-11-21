"""主动学习候选队列（导师方案第3步）。

LatinHypercube 采样 A/B/Cl/Br/I 组分空间 → Δ 模型不确定性 + 目标带隙窗口筛选 → DFT 计算队列。
候选特征用训练集均值行近似（结构描述子不可得），hse_est 用 PBE 均值近似，均如实标注。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from scipy.stats import qmc

from src.data.preprocessor import A_SITES, B_SITES
from src.models.delta import build_estimator


def build_queue(data: Dict[str, Any], cfg: Dict[str, Any],
                out_csv: Path, n_candidates: int = 2000,
                top_n: int = 30) -> Dict[str, Any]:
    """生成主动学习 DFT 计算队列 CSV，返回摘要。"""
    sampler = qmc.LatinHypercube(d=3, seed=cfg["model"]["random_state"])
    u = sampler.random(n=n_candidates)
    cl = u[:, 0] * 3.0
    br = u[:, 1] * (3.0 - cl)
    i = 3.0 - cl - br
    rng = np.random.default_rng(cfg["model"]["random_state"])
    a_idx = rng.integers(0, len(A_SITES), n_candidates)
    b_idx = rng.integers(0, len(B_SITES), n_candidates)

    est = build_estimator(cfg)
    est.fit(data["X_pair"], data["delta"])
    names = data["names"]
    base = data["X_pair"].mean(axis=0)
    cand = np.tile(base, (n_candidates, 1))
    for k, s in enumerate(A_SITES):
        if f"A_{s}" in names:
            cand[:, names.index(f"A_{s}")] = (a_idx == k).astype(float)
    for k, s in enumerate(B_SITES):
        if f"B_{s}" in names:
            cand[:, names.index(f"B_{s}")] = (b_idx == k).astype(float)
    for nm, vals in (("Cl_ratio", cl), ("Br_ratio", br), ("I_ratio", i)):
        if nm in names:
            cand[:, names.index(nm)] = vals

    dp = np.asarray(est.predict(cand), float)
    std = np.std([t.predict(cand) for t in est.estimators_], axis=0) \
        if hasattr(est, "estimators_") else np.zeros(n_candidates)
    hse_est = float(data["y_pbe_pair"].mean()) + dp
    in_window = (hse_est >= 1.3) & (hse_est <= 1.5)
    score = std + 0.1 * in_window.astype(float)
    sel = np.argsort(-score)[:top_n]

    queue = pd.DataFrame({
        "rank": range(1, len(sel) + 1),
        "A_site": [A_SITES[a_idx[j]] for j in sel],
        "B_site": [B_SITES[b_idx[j]] for j in sel],
        "Cl": np.round(cl[sel], 3), "Br": np.round(br[sel], 3), "I": np.round(i[sel], 3),
        "hse_est_ev": np.round(hse_est[sel], 3),
        "uncertainty_ev": np.round(std[sel], 3),
        "in_target_window": np.where(in_window[sel], "yes", "no"),
        "priority_note": "按不确定性降序；目标带隙窗口作加分；τ与HSE均为近似，需DFT精算",
    })
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    queue.to_csv(out_csv, index=False, encoding="utf-8-sig")
    return dict(
        experiment_id="AL-queue",
        n_candidates=int(n_candidates), n_selected=int(len(sel)),
        n_in_target_window=int(in_window[sel].sum()),
        selection_rule="不确定性Top30；目标带隙1.3-1.5 eV作加分项（非硬门限）",
        caveat="候选特征用训练集均值行近似；hse_est用PBE均值近似，落入目标窗口候选偏少；"
               "仅供DFT计算排序，不构成精度结论",
        csv=str(out_csv),
    )
