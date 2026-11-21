"""Δ-learning 双模型（导师方案主线）。

HSE = PBE + Δ；训练两个 RF：PBE 基线模型（全量）+ Δ 模型（配对样本）。
推理口径分隔：oracle(PBE真值+Δ) 与 end_to_end(PBE预测+Δ)，不可混用。
"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

MODELS = {
    "random_forest": RandomForestRegressor,
    "gradient_boosting": GradientBoostingRegressor,
}


def build_estimator(cfg: Dict[str, Any], n_estimators: int | None = None,
                    sample_weight: bool = False):
    """按配置构造 estimator。in: cfg, 覆盖的树数 -> out: 未训练 estimator。"""
    m = cfg["model"]
    kind = m["type"]
    if kind == "xgboost":
        try:
            from xgboost import XGBRegressor
        except ImportError:
            kind = "random_forest"
        else:
            est = XGBRegressor(
                n_estimators=n_estimators or m["n_estimators"],
                max_depth=m.get("max_depth", 6), learning_rate=0.1,
                subsample=0.8, colsample_bytree=0.8,
                random_state=m["random_state"], n_jobs=m["n_jobs"],
            )
            return est
    cls = MODELS.get(kind, RandomForestRegressor)
    return cls(
        n_estimators=n_estimators or m["n_estimators"],
        max_depth=m["max_depth"],
        random_state=m["random_state"],
        n_jobs=m.get("n_jobs", -1),
    )


def fit_fold(X_tr: np.ndarray, delta_tr: np.ndarray,
             X_te: np.ndarray, cfg: Dict[str, Any],
             w_tr: np.ndarray | None = None,
             n_estimators: int | None = None) -> np.ndarray:
    """单折训练 Δ 模型并返回 Δ 预测。in: 折内特征/标签/配置 -> out: Δ_pred。"""
    est = build_estimator(cfg, n_estimators=n_estimators)
    if w_tr is not None:
        est.fit(X_tr, delta_tr, sample_weight=w_tr)
    else:
        est.fit(X_tr, delta_tr)
    return np.asarray(est.predict(X_te), float)
