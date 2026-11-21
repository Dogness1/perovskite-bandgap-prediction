"""电子描述子（导师方案 P1-3 / 优化方案第3步）。

元素电负性取 Pauling 标度；MA/FA 用组成元素原子数加权平均（近似）。
这些是文献常识性数值，不是本项目实测结果；MA/FA 的近似已在注释标明，
按宪法 1.1 作 provenance 声明，不冒充核验数据。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ELECTRONEG = {
    "Cs": 0.79, "Rb": 0.82, "K": 0.82, "Na": 0.93,
    "MA": 2.37, "FA": 2.49,  # C/N/H 按原子数加权近似
    "Pb": 2.33, "Sn": 1.96, "Ge": 2.01, "Ca": 1.00, "Sr": 0.95, "Ba": 0.89,
    "Cd": 1.69, "Zn": 1.65, "Mg": 1.31, "Cu": 1.90, "Ni": 1.91, "Fe": 1.83,
    "Mn": 1.55, "Co": 1.88,
    "Cl": 3.16, "Br": 2.96, "I": 2.66,
}
VALENCE = {
    "Cs": 1, "Rb": 1, "K": 1, "Na": 1, "MA": 5, "FA": 8,
    "Pb": 4, "Sn": 4, "Ge": 4, "Ca": 2, "Sr": 2, "Ba": 2,
    "Cd": 2, "Zn": 2, "Mg": 2, "Cu": 1, "Ni": 2, "Fe": 2, "Mn": 2, "Co": 2,
}


def electronic_features(df: pd.DataFrame) -> pd.DataFrame:
    """返回 5 维电子描述子 DataFrame，列顺序与配置一致。"""
    a_chi = df["A_site"].map(ELECTRONEG).fillna(0.0).to_numpy(float)
    b_chi = df["B_site"].map(ELECTRONEG).fillna(0.0).to_numpy(float)
    cl = pd.to_numeric(df["Cl_ratio"], errors="coerce").fillna(0.0).to_numpy(float)
    br = pd.to_numeric(df["Br_ratio"], errors="coerce").fillna(0.0).to_numpy(float)
    i = pd.to_numeric(df["I_ratio"], errors="coerce").fillna(0.0).to_numpy(float)
    h_chi = (cl * ELECTRONEG["Cl"] + br * ELECTRONEG["Br"] + i * ELECTRONEG["I"]) / 3.0
    a_val = df["A_site"].map(VALENCE).fillna(0.0).to_numpy(float)
    b_val = df["B_site"].map(VALENCE).fillna(0.0).to_numpy(float)
    return pd.DataFrame({
        "A_electroneg": a_chi,
        "B_electroneg": b_chi,
        "chi_B_minus_A": b_chi - a_chi,
        "halogen_electroneg": h_chi,
        "valence_A_plus_B": a_val + b_val,
    }, index=df.index)
