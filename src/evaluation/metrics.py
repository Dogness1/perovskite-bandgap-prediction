"""评估指标：R²/MAE/RMSE 与验收线判定（按 docs/acceptance.md 上修口径）。"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# 上修验收线（DEC-v3-001，见 docs/acceptance.md）
# 口径对标：导师文档3验收线历史上按 oracle_pbe（PBE_true + Δ_pred）报告
# （provenance: 指标对账_v3.0 §1"C1 随机CV 0.9398 落在 0.90-0.94 上沿"；
#  v2.0 CHANGELOG"此前报告的数字都属于场景A"）。end_to_end 是部署口径，另报不拿此线判定。
ACCEPTANCE = {
    "random_cv": {"r2": (0.90, 0.94), "mae": (0.29, 0.37)},
    "group_cv": {"r2": (0.75, 0.85), "mae": (0.47, 0.60)},
    "external": {"r2": (0.70, 0.82), "mae": (0.52, 0.66)},
}


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """in: y_true(n,), y_pred(n,) -> out: {r2,mae,rmse,n}"""
    return dict(
        r2=float(r2_score(y_true, y_pred)),
        mae=float(mean_absolute_error(y_true, y_pred)),
        rmse=float(np.sqrt(mean_squared_error(y_true, y_pred))),
        n=int(len(y_true)),
    )


def judge(view: str, m: Dict[str, Any]) -> Dict[str, Any]:
    """按上修验收线判定是否达标。MAE 越小越好，低于区间下界视为更优。"""
    band = ACCEPTANCE[view]
    r2_lo, r2_hi = band["r2"]
    mae_lo, mae_hi = band["mae"]
    r2_ok = r2_lo <= m["r2"] <= r2_hi or m["r2"] > r2_hi
    mae_ok = m["mae"] <= mae_hi  # 越小越好
    return dict(
        r2_in_band=r2_lo <= m["r2"] <= r2_hi,
        r2_pass=bool(r2_ok),
        mae_in_band=mae_lo <= m["mae"] <= mae_hi,
        mae_pass=bool(mae_ok),
        overall_pass=bool(r2_ok and mae_ok),
        band=band,
        note="R²沿用导师区间，MAE按std=1.4746反推上修；见docs/acceptance.md",
    )
