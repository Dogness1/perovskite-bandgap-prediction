"""化学式解析与特征构造（34 维基线 + 结构默认值学习）。"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

A_SITES = ["MA", "FA", "Cs", "Rb", "K", "Na"]
B_SITES = ["Ge", "Sn", "Pb", "Ca", "Sr", "Ba", "Cd", "Zn", "Mg", "Cu", "Ni", "Fe", "Mn", "Co"]
HALOGENS = ["Cl", "Br", "I"]
ION_RADII = {
    "MA": 2.17, "FA": 2.53, "Cs": 1.67, "Rb": 1.52, "K": 1.38, "Na": 1.02,
    "Ge": 0.73, "Sn": 0.93, "Pb": 1.19, "Ca": 1.00, "Sr": 1.18, "Ba": 1.35,
    "Cd": 0.95, "Zn": 0.74, "Mg": 0.72, "Cu": 0.73, "Ni": 0.69, "Fe": 0.78,
    "Mn": 0.83, "Co": 0.745,
    "Cl": 1.81, "Br": 1.96, "I": 2.20,
}
STRUCT_COLS = [
    "Deviation of Cubicity b axis", "Deviation of Cubicity c axis",
    "Deviation of Cubicity at alpha", "Deviation of Cubicity at beta",
    "Deviation of Cubicity at gamma", "Octaehdral Factor",
    "Tolerance Factor", "Bartel's Tolerance Factor",
]


def parse_formula(formula: str) -> Dict[str, object]:
    """解析 ABX3 钙钛矿化学式，含混合 A 位的 B 位回退解析。"""
    import re
    result: Dict[str, object] = {
        "A_site": None, "B_site": None,
        "Cl_ratio": 0.0, "Br_ratio": 0.0, "I_ratio": 0.0,
        "is_mixed_halogen": False,
    }
    rest = str(formula).strip()
    for a in sorted(A_SITES, key=len, reverse=True):
        if rest.startswith(a):
            result["A_site"] = a
            rest = rest[len(a):]
            break
    for b in sorted(B_SITES, key=len, reverse=True):
        if rest.startswith(b):
            result["B_site"] = b
            rest = rest[len(b):]
            break
    if result["B_site"] is None:  # 混合 A 位回退
        alt = "|".join(sorted(B_SITES, key=len, reverse=True))
        m = re.search(rf"({alt})(?=Cl|Br|I)", rest)
        if m:
            result["B_site"] = m.group(1)
    count = 0
    for h in HALOGENS:
        m = re.search(rf"{h}_(\d+\.?\d*)", rest)
        if m:
            result[f"{h}_ratio"] = float(m.group(1))
            count += 1
    result["is_mixed_halogen"] = count > 1
    return result


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """对 DataFrame 的 Formula 列追加解析字段（不改原始列）。"""
    parsed = pd.DataFrame([parse_formula(f) for f in df["Formula"]])
    return pd.concat([df.reset_index(drop=True), parsed], axis=1)


def fit_structure_defaults(df: pd.DataFrame) -> Dict[str, float]:
    """学习 8 个结构描述子的训练均值，作推理时的中性填充。"""
    return {
        c: (float(pd.to_numeric(df[c], errors="coerce").mean()) if c in df.columns else 0.0)
        for c in STRUCT_COLS
    }


def create_feature_matrix(
    df: pd.DataFrame,
    include_electronic: bool = False,
    structure_defaults: Dict[str, float] | None = None,
) -> Tuple[np.ndarray, List[str]]:
    """构造特征矩阵。in: 解析后的df, 是否加电子描述子, 结构默认值 -> out: (X(d维), names)。"""
    features: List[pd.DataFrame] = []
    a_dum = pd.get_dummies(df["A_site"], prefix="A")
    for a in A_SITES:
        if f"A_{a}" not in a_dum.columns:
            a_dum[f"A_{a}"] = 0
    features.append(a_dum[[f"A_{a}" for a in A_SITES]])
    b_dum = pd.get_dummies(df["B_site"], prefix="B")
    for b in B_SITES:
        if f"B_{b}" not in b_dum.columns:
            b_dum[f"B_{b}"] = 0
    features.append(b_dum[[f"B_{b}" for b in B_SITES]])
    features.append(df[["Cl_ratio", "Br_ratio", "I_ratio"]].astype(float))

    work = df.copy()
    work["A_radius"] = work["A_site"].map(ION_RADII)
    work["B_radius"] = work["B_site"].map(ION_RADII)
    total = (work["Cl_ratio"] + work["Br_ratio"] + work["I_ratio"]).astype(float)
    weighted = (work["Cl_ratio"] * ION_RADII["Cl"] + work["Br_ratio"] * ION_RADII["Br"]
                + work["I_ratio"] * ION_RADII["I"])
    work["avg_halogen_radius"] = np.divide(
        weighted, total, out=np.zeros(len(work)), where=total.to_numpy() > 0)
    features.append(work[["A_radius", "B_radius", "avg_halogen_radius"]])

    defaults = structure_defaults or {}
    struct = pd.DataFrame(index=df.index)
    for c in STRUCT_COLS:
        struct[c] = pd.to_numeric(df[c], errors="coerce") if c in df.columns else np.nan
        struct[c] = struct[c].fillna(defaults.get(c, 0.0))
    features.append(struct)

    if include_electronic:
        from src.data.electronic import electronic_features
        features.append(electronic_features(df))

    X_df = pd.concat(features, axis=1)
    X = np.nan_to_num(X_df.to_numpy(float), nan=0.0, posinf=0.0, neginf=0.0)
    return X, X_df.columns.tolist()
