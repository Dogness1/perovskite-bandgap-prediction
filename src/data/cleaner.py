"""数据质量校验（导师方案第0步）：Δ 按 B 位分层的 3σ 候选、τ 异常、收敛占位。"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from src.data.preprocessor import STRUCT_COLS


def audit_labels(df: pd.DataFrame) -> Dict[str, Any]:
    """按 B 位分层统计 Δ，标出 3σ 候选（只标不删）与 τ 异常。"""
    rows: List[Dict[str, Any]] = []
    candidates: List[Dict[str, Any]] = []
    for b, grp in df.groupby("B_site"):
        mu, sd = grp["delta"].mean(), grp["delta"].std(ddof=1)
        lo, hi = mu - 3 * sd, mu + 3 * sd
        rows.append(dict(B_site=str(b), n=int(len(grp)), mean=float(mu), std=float(sd),
                         low_3sigma=float(lo), high_3sigma=float(hi)))
        for _, r in grp.iterrows():
            if r["delta"] < lo or r["delta"] > hi:
                candidates.append(dict(formula=str(r["Formula"]), B_site=str(b),
                                       delta=float(r["delta"]),
                                       z=float((r["delta"] - mu) / sd),
                                       action="待人工回查，不自动删除"))
    tau = pd.to_numeric(df.get("Tolerance Factor", pd.Series([np.nan] * len(df))), errors="coerce")
    tau_flag = int(((tau < 0.4) | (tau > 1.1)).sum())
    return dict(
        by_B_site=rows,
        outlier_3sigma_candidates=candidates,
        outlier_count=len(candidates),
        tau_anomaly_count=tau_flag,
        tau_rule="tau<0.4 or tau>1.1（标记不删除）",
        is_converged="unknown（无法核验各样本 DFT 收敛参数，数据版本已知缺口）",
        action_note="只标记交人工回查；禁止按残差删样本刷 R²（宪法7）",
    )
