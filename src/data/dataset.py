"""数据集组装：配对切分 + 缩放 + 分组标签，供评估与 API 共用。"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src.config import ROOT
from src.data.loader import load_pairs
from src.data.preprocessor import extract_features, create_feature_matrix, fit_structure_defaults


def build_dataset(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """从配置加载并组装完整数据集。

    out: dict{
      X_pair(n_pair,d), X_unpair(n_unpair,d), y_pbe_pair, y_unpair, y_hse, delta,
      groups(object A_B), b_site, structure_defaults, names, n_pair, n_unpair, d
    }
    """
    pairs = load_pairs(cfg)
    df = pairs["df"]
    parsed = extract_features(df)
    defaults = fit_structure_defaults(df)

    # 非配对样本：PBE 全量中不在 HSE 的那些，用于训练 PBE 基线模型
    dpath = ROOT / cfg["data"]["path"]
    pbe_all = pd.read_excel(dpath, sheet_name=cfg["data"]["sheet_pbe"])
    key = cfg["data"]["key"]
    unpaired = pbe_all[~pbe_all[key].isin(pairs["formulas"])].reset_index(drop=True)
    unp_parsed = extract_features(unpaired)

    inc_e = cfg["features"].get("include_electronic", False)
    X_pair, names = create_feature_matrix(parsed, inc_e, defaults)
    X_unpair, names_u = create_feature_matrix(unp_parsed, inc_e, defaults)
    assert names == names_u, "配对/非配对特征列不一致"

    scaler = StandardScaler()
    X_pair_s = scaler.fit_transform(X_pair)
    X_unpair_s = scaler.transform(X_unpair)

    groups = np.array(
        [f"{a}_{b}" for a, b in zip(parsed["A_site"], parsed["B_site"])], dtype=object)
    b_site = parsed["B_site"].astype(str).to_numpy()
    y_unpair = unpaired[cfg["data"]["pbe_target"]].to_numpy(float)

    return dict(
        X_pair=X_pair_s, X_unpair=X_unpair_s,
        y_pbe_pair=pairs["pbe"], y_unpair=y_unpair,
        y_hse=pairs["hse"], delta=pairs["delta"],
        groups=groups, b_site=b_site,
        structure_defaults=defaults, names=names,
        cl_raw=pd.to_numeric(parsed["Cl_ratio"], errors="coerce").to_numpy(float),
        br_raw=pd.to_numeric(parsed["Br_ratio"], errors="coerce").to_numpy(float),
        scaler=scaler,
        n_pair=len(pairs["pbe"]), n_unpair=len(y_unpair), d=len(names),
    )


def grid_weights(data: Dict[str, Any]) -> np.ndarray:
    """卤素 10x10 网格密度倒数权重（导师文档3方案1），均值为1。"""
    bx = np.clip((data["cl_raw"] / 3.0 * 10).astype(int), 0, 9)
    by = np.clip((data["br_raw"] / 3.0 * 10).astype(int), 0, 9)
    cnt = np.zeros((10, 10), float)
    for a, b in zip(bx, by):
        cnt[a, b] += 1
    w = np.array([1.0 / max(cnt[a, b], 1.0) for a, b in zip(bx, by)])
    return w / w.mean()
