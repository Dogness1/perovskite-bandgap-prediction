"""三套验证（导师文档3）：随机10x5插值、GroupKFold化学外推、group-disjoint外部集。

统一在同一评估器函数里产出两套口径：
  end_to_end = PBE_pred + Δ_pred（主指标，API默认场景）
  oracle_pbe = PBE_true + Δ_pred（有PBE结果时的Δ-learning上限）
PBE 基线模型在每折训练集重训，不泄露测试折 PBE 标签。
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, Tuple

import numpy as np
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, RepeatedKFold

from src.models.delta import build_estimator, fit_fold
from src.evaluation.metrics import compute_metrics


def _run_split(data: Dict[str, Any], cfg: Dict[str, Any],
               splits: Iterator[Tuple[np.ndarray, np.ndarray]],
               n_estimators: int, max_folds: int | None = None) -> Dict[str, Any]:
    ys, pbe_e2e, pbe_oracle = [], [], []
    for k, (tr, te) in enumerate(splits):
        # PBE 基线模型：非配对样本 + 配对训练折，不含测试折 PBE 标签
        X_pbe_tr = np.vstack([data["X_unpair"], data["X_pair"][tr]])
        y_pbe_tr = np.concatenate([data["y_unpair"], data["y_pbe_pair"][tr]])
        pbe_m = build_estimator(cfg, n_estimators=n_estimators)
        pbe_m.fit(X_pbe_tr, y_pbe_tr)
        dp = fit_fold(data["X_pair"][tr], data["delta"][tr], data["X_pair"][te],
                      cfg, n_estimators=n_estimators)
        ys.append(data["y_hse"][te])
        pbe_e2e.append(pbe_m.predict(data["X_pair"][te]) + dp)
        pbe_oracle.append(data["y_pbe_pair"][te] + dp)
        if max_folds and k + 1 >= max_folds:
            break
    y = np.concatenate(ys)
    return dict(
        end_to_end=compute_metrics(y, np.concatenate(pbe_e2e)),
        oracle_pbe=compute_metrics(y, np.concatenate(pbe_oracle)),
        folds=len(ys),
    )


def run_evaluation(data: Dict[str, Any], cfg: Dict[str, Any],
                   dry: bool = False) -> Dict[str, Any]:
    """执行三套验证。in: data(dict), cfg(dict), dry(bool) -> out: 结果dict。"""
    ev = cfg["evaluation"]
    n_est = 10 if dry else cfg["model"]["n_estimators"]
    reps = 1 if dry else ev["random_cv"]["n_repeats"]
    seed = ev["random_cv"]["seed"]
    max_folds = 1 if dry else None

    rkf = RepeatedKFold(n_splits=ev["random_cv"]["n_splits"], n_repeats=reps,
                       random_state=seed)
    random_cv = _run_split(data, cfg, rkf.split(data["X_pair"]), n_est, max_folds)

    gkf = GroupKFold(n_splits=ev["group_cv"]["n_splits"])
    group_cv = _run_split(
        data, cfg, gkf.split(data["X_pair"], data["delta"], groups=data["groups"]),
        n_est, max_folds,
    )

    result = dict(
        experiment_id=cfg.get("experiment_id", "base"),
        config=dict(model=cfg["model"], features=cfg["features"],
                    evaluation=ev, seed=seed),
        n_pair=data["n_pair"], n_unpair=data["n_unpair"], d=data["d"],
        n_estimators=n_est, n_repeats=reps,
        basis={"end_to_end": "PBE_pred + Δ_pred（主指标）",
               "oracle_pbe": "PBE_true + Δ_pred"},
        random_cv=random_cv, group_cv=group_cv,
    )

    holdout = ev["external"].get("holdout_groups", [])
    if holdout:
        mask = ~np.isin(data["groups"], holdout)
        tr_idx, te_idx = np.where(mask)[0], np.where(~mask)[0]
        X_pbe_tr = np.vstack([data["X_unpair"], data["X_pair"][tr_idx]])
        y_pbe_tr = np.concatenate([data["y_unpair"], data["y_pbe_pair"][tr_idx]])
        pbe_m = build_estimator(cfg, n_estimators=n_est)
        pbe_m.fit(X_pbe_tr, y_pbe_tr)
        dp = fit_fold(data["X_pair"][tr_idx], data["delta"][tr_idx],
                      data["X_pair"][te_idx], cfg, n_estimators=n_est)
        result["external"] = dict(
            holdout_groups=holdout,
            end_to_end=compute_metrics(data["y_hse"][te_idx],
                                       pbe_m.predict(data["X_pair"][te_idx]) + dp),
            oracle_pbe=compute_metrics(data["y_hse"][te_idx],
                                       data["y_pbe_pair"][te_idx] + dp),
            note="group-disjoint 划组；非独立数据源，按导师规则不作论文最终泛化主结论",
        )
    return result
