"""推理封装：启动时训练 PBE+Δ 双模型，提供预测/生成/统计。"""
from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from src.config import ROOT, load_config
from src.data.dataset import build_dataset
from src.data.preprocessor import (
    A_SITES, B_SITES, HALOGENS, ION_RADII, STRUCT_COLS, parse_formula)
from src.models.delta import build_estimator

# API 短参数名 -> 结构描述子列名
STRUCTURE_PARAM_MAP = {
    "cubicity_b": "Deviation of Cubicity b axis",
    "cubicity_c": "Deviation of Cubicity c axis",
    "cubicity_alpha": "Deviation of Cubicity at alpha",
    "cubicity_beta": "Deviation of Cubicity at beta",
    "cubicity_gamma": "Deviation of Cubicity at gamma",
    "octahedral_factor": "Octaehdral Factor",
    "tolerance_factor": "Tolerance Factor",
    "bartel_tolerance": "Bartel's Tolerance Factor",
}


class PredictorService:
    """持有训练好的 PBE 基线模型与 Δ 模型，提供 HSErel_SOC 预测。"""

    def __init__(self, cfg: Dict[str, Any] | None = None):
        self.cfg = cfg or load_config("base.json")
        self.data = build_dataset(self.cfg)
        self.pbe_model = build_estimator(self.cfg)
        self.pbe_model.fit(
            np.vstack([self.data["X_unpair"], self.data["X_pair"]]),
            np.concatenate([self.data["y_unpair"], self.data["y_pbe_pair"]]))
        self.delta_model = build_estimator(self.cfg)
        self.delta_model.fit(self.data["X_pair"], self.data["delta"])
        self.defaults = self.data["structure_defaults"]

    def structure_values(self, payload: Dict[str, Any]) -> Dict[str, float]:
        """从请求提取结构描述子，缺省用训练均值。"""
        out = {}
        for param, col in STRUCTURE_PARAM_MAP.items():
            v = payload.get(param)
            if v is not None:
                try:
                    out[col] = float(v)
                    continue
                except (TypeError, ValueError):
                    pass
            out[col] = self.defaults.get(col, 0.0)
        return out

    def predict_one(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """单条预测：返回 HSE = PBE(真值或预测) + Δ。"""
        a = payload.get("a_site", "Cs")
        b = payload.get("b_site", "Pb")
        cl = float(payload.get("cl_ratio", 0))
        br = float(payload.get("br_ratio", 0))
        i = float(payload.get("i_ratio", 0))
        row = dict(Formula=f"{a}{b}Cl_{cl}Br_{br}I_{i}", A_site=a, B_site=b,
                   Cl_ratio=cl, Br_ratio=br, I_ratio=i, **self.structure_values(payload))
        df = pd.DataFrame([row])
        from src.data.preprocessor import create_feature_matrix
        X, _ = create_feature_matrix(df, self.cfg["features"].get("include_electronic", False),
                                     self.defaults)
        Xs = self.data["scaler"].transform(X)
        pbe_pred = float(self.pbe_model.predict(Xs)[0])
        dp = float(self.delta_model.predict(Xs)[0])
        override = payload.get("pbe_bandgap")
        if override is not None:
            pbe_base, source = float(override), "provided"
        else:
            pbe_base, source = pbe_pred, "predicted"
        struct_source = "provided" if any(payload.get(p) is not None
                                          for p in STRUCTURE_PARAM_MAP) else "default_mean"
        return dict(
            formula=f"{a}{b}(Cl_{cl}Br_{br}I_{i})",
            predicted_bandgap=pbe_base + dp,
            bandgap_basis="HSErel_SOC (PBE + Δ-learning)",
            pbe_source=source, structure_source=struct_source,
            pbe_bandgap=pbe_base, delta_correction=dp,
            input=dict(a_site=a, b_site=b, cl_ratio=cl, br_ratio=br, i_ratio=i),
        )
