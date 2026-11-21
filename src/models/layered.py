"""B 位分层 Δ 模型（导师方案：按 B 位元素分别建基线）。"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np

from src.models.delta import build_estimator


def layered_fit_predict(X: np.ndarray, delta: np.ndarray, b_site: np.ndarray,
                        cfg: Dict[str, Any], splitter_factory,
                        n_estimators: int | None = None) -> Dict[str, Any]:
    """按 B 位分层逐层训练 Δ 模型，拼接 OOF 预测。

    in: X(n,d), delta(n,), b_site(n,)字符串, cfg, splitter_factory(折数生成器), 树数
    out: dict{pred(n,), per_group{...}, note}
    样本数小于折数的层用全量拟合回代（乐观估计，明确标注）。
    """
    pred = np.zeros(len(X), dtype=float)
    per_group: Dict[str, Any] = {}
    for b in sorted(set(b_site)):
        mask = b_site == b
        idx = np.where(mask)[0]  # 真实索引，避免链式索引写副本
        Xb, db = X[idx], delta[idx]
        n = len(db)
        per_group[str(b)] = int(n)
        if n < 2:
            pred[idx] = db.mean()
            continue
        folds = min(5, n)
        if folds < 2:
            est = build_estimator(cfg, n_estimators=n_estimators)
            est.fit(Xb, db)
            pred[idx] = np.asarray(est.predict(Xb), float)
            continue
        for tr, te in splitter_factory(n_splits=folds).split(Xb):
            est = build_estimator(cfg, n_estimators=n_estimators)
            est.fit(Xb[tr], db[tr])
            pred[idx[te]] = np.asarray(est.predict(Xb[te]), float)
    return dict(pred=pred, per_group=per_group,
                note="样本不足的层全量回代（乐观），不与全局口径直接对比")
