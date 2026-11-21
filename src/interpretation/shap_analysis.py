"""SHAP 可解释性（导师方案第2步诊断 + P1 可解释性前提）。"""
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from src.models.delta import build_estimator


def explain_delta(X: np.ndarray, delta: np.ndarray, names: List[str],
                  cfg: Dict[str, Any], top_k: int = 12) -> Dict[str, Any]:
    """对 Δ 模型做 TreeExplainer，返回特征贡献排名。不产出精度结论。"""
    import shap
    est = build_estimator(cfg)
    est.fit(X, delta)
    explainer = shap.TreeExplainer(est)
    values = explainer.shap_values(X, check_additivity=False)
    if isinstance(values, list):
        values = values[0]
    mean_abs = np.abs(np.asarray(values)).mean(axis=0)
    order = np.argsort(-mean_abs)[:top_k]
    ranking = [dict(feature=names[j], mean_abs_shap=float(mean_abs[j])) for j in order]
    return dict(
        method="shap.TreeExplainer",
        target="delta (Δ = HSE - PBE)",
        top_features=ranking,
        note="事后解释，不改变评估器、不产出新精度；结构描述子排名高但推理时依赖填充值",
    )
