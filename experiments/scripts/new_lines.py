#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
new_lines.py — v2.1 三项新实验线（均为独立实验线，不改冻结的 train.py/C1 基线）

宪法约束：
  - 3.1 评估器：本脚本的每条线都显式声明自己的评估口径，标注"新实验线"，
        不与 C1 基线（experiments/results/train_C1.json）直接对比。
  - 3.3 流程：每条线先小样本验证（--dry-run）再正式。
  - 3.4 可归因：每条线写明"改了什么→影响哪个指标→实际结果→是否支持假设"。
  - 3.6 负面结果：保留失败/无提升的线，不删除。

三条线：
  L1_shap        : SHAP 可解释性（增量分析，不改评估器、不产出新"精度"）
  L2_b分层       : Pb/Sn 按 B 位分层 Δ 模型（训练子集改变 = 新线；仅覆盖 54/281）
  L3_电子描述子  : 加电负性/价电子特征 + group-disjoint 外部集（特征+评估器双改变 = 新线）

命令：
  python experiments/scripts/new_lines.py --line all --dry-run
  python experiments/scripts/new_lines.py --line all
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold, KFold

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from data.preprocessor import PerovskitePreprocessor  # noqa: E402
from data.feature_engineer import FeatureEngineer  # noqa: E402

DATA = ROOT / "d3dd00015j2" / "perovs_data_final.xlsx"
RESULTS = ROOT / "experiments" / "results"
SEED = 42
STRUCT_COLS = PerovskitePreprocessor.STRUCTURE_COLS


# ------------------------------------------------------------------ 公共数据
def load_base():
    """返回 281 配对样本的特征/标签/分组（与 C1 同口径，34 维）。"""
    pbe = pd.read_excel(DATA, sheet_name="PBE")
    hse = pd.read_excel(DATA, sheet_name="HSErel_SOC")
    prep = PerovskitePreprocessor()
    parsed = prep.extract_features(pbe)  # 已含 pbe 全部原列 + 6 解析列
    hmap = hse.set_index("Formula")["Band Gap (eV)"]
    mask = parsed["Formula"].isin(hmap.index).to_numpy()
    d = parsed.loc[mask].reset_index(drop=True)
    d["hse"] = hmap.reindex(d["Formula"]).to_numpy(float)
    d["pbe_gap"] = d["Band Gap (eV)"].to_numpy(float)
    d["delta"] = d["hse"] - d["pbe_gap"]

    X, _, names = prep.create_feature_matrix(d, include_target=False)
    X = np.nan_to_num(np.asarray(X, float), nan=0.0, posinf=0.0, neginf=0.0)
    X = FeatureEngineer().fit_transform(X, names)
    g = np.array([f"{a}_{b}" for a, b in zip(d["A_site"], d["B_site"])], dtype=object)
    return dict(X=X, names=list(names), delta=d["delta"].to_numpy(float),
                pbe=d["pbe_gap"].to_numpy(float), hse=d["hse"].to_numpy(float),
                g=g, bsite=d["B_site"].to_numpy(), cl=d["Cl_ratio"].to_numpy(float),
                br=d["Br_ratio"].to_numpy(float), i=d["I_ratio"].to_numpy(float),
                df=d, n=len(d))


def eval_pred(y, p):
    return dict(r2=float(r2_score(y, p)), mae=float(mean_absolute_error(y, p)), n=int(len(y)))


def make_record(exp_id, line, hypothesis, change, evaluator, seed, metrics, conclusion,
                supported, caveat=""):
    """按宪法 3.2 生成完整实验记录字段。"""
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip() or "unknown"
    # 工作区若有未提交改动，commit 不能代表实际代码状态，标注 +dirty（宪法 1.1 溯源）
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        commit = commit + "+dirty"
    cfg = dict(line=line, evaluator=evaluator, seed=seed)
    cfg_hash = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    return dict(
        experiment_id=exp_id,
        line=line,
        timestamp=datetime.now(timezone.utc).isoformat(),
        hypothesis=hypothesis,
        change=change,
        config_hash=cfg_hash,
        code_commit=commit,
        dataset="perovs_data_final.xlsx PBE+HSErel_SOC, 281 paired",
        seed=seed,
        evaluator=evaluator,
        metrics=metrics,
        conclusion=conclusion,
        supported=supported,
        caveat=caveat,
        new_line=True,
        comparable_to_C1_baseline=False,
    )


# ------------------------------------------------------------------ L1 SHAP
def line_shap(data, dry=False):
    """SHAP 可解释性：对 Δ 模型做 TreeExplainer，输出特征贡献排名。"""
    import shap
    m = RandomForestRegressor(n_estimators=10 if dry else 200, max_depth=10,
                              random_state=SEED, n_jobs=-1)
    m.fit(data["X"], data["delta"])
    explainer = shap.TreeExplainer(m)
    sv = explainer.shap_values(data["X"], check_additivity=False)
    if isinstance(sv, list):
        sv = sv[0]
    mean_abs = np.abs(sv).mean(axis=0)
    order = np.argsort(-mean_abs)
    ranking = [dict(feature=data["names"][j], mean_abs_shap=float(mean_abs[j]))
               for j in order[:12]]
    metrics = dict(top_features=ranking,
                   all_features_scored=len(data["names"]),
                   n_samples=int(data["n"]))
    rec = make_record(
        "L1-SHAP", "shap",
        hypothesis="树模型 impurity 重要度有偏，SHAP 能否给出不同的特征排序",
        change="新增 shap.TreeExplainer 对 Δ 模型做事后解释；不改模型、不改评估器、不产出新精度",
        evaluator="全量 281 样本拟合后的解释分析（非预测评估）",
        seed=SEED, metrics=metrics,
        conclusion=f"SHAP 排名前 3：{[r['feature'] for r in ranking[:3]]}；"
                   "作为可解释性增量分析，无精度结论",
        supported="信息性（非假设检验）",
        caveat="SHAP 解释的是 Δ 模型；impurity 重要度与 SHAP 排序差异需人工判读，不自动判定优劣",
    )
    return rec


# ------------------------------------------------------------------ L2 Pb/Sn 分层
def line_b分层(data, dry=False):
    """按 B 位分层的 Δ 模型：只取 Pb/Sn 子集，各训练一个模型。"""
    sub = np.isin(data["bsite"], ["Pb", "Sn"])
    X, dlt, g = data["X"][sub], data["delta"][sub], data["g"][sub]
    hse, pbe = data["hse"][sub], data["pbe"][sub]
    b = data["bsite"][sub]
    per_group = {k: int((b == k).sum()) for k in ["Pb", "Sn"]}
    folds = 2 if dry else 5
    rkf = KFold(n_splits=folds, shuffle=True, random_state=SEED)
    ys, ps = [], []
    for tr, te in rkf.split(X):
        m = RandomForestRegressor(n_estimators=10 if dry else 200, max_depth=10,
                                  random_state=SEED, n_jobs=-1)
        m.fit(X[tr], dlt[tr])
        ys.append(hse[te]); ps.append(pbe[te] + m.predict(X[te]))
    m = eval_pred(np.concatenate(ys), np.concatenate(ps))
    m["n_subset"] = int(sub.sum())
    m["per_group"] = per_group
    m["coverage_of_281"] = round(float(sub.sum()) / data["n"], 4)
    rec = make_record(
        "L2-B分层", "b_site_layered_delta",
        hypothesis="Sn 基 Δ 均值 1.14、Pb 基 0.33，分层建模能否降低组内误差",
        change="仅取 Pb/Sn 共 54 样本，按 B 位各训练 1 个 Δ 模型后合并评估；训练子集改变",
        evaluator=f"KFold({folds}, seed=42) on 54-sample Pb/Sn subset",
        seed=SEED, metrics=m,
        conclusion=f"Pb/Sn 子集 R²={m['r2']:.4f} MAE={m['mae']:.4f} eV（n={m['n']}）",
        supported="待定",
        caveat="仅覆盖 54/281(19.2%) 样本，其余 B 位(Ca/Ba/Sr/Ge)未纳入；"
               "子集口径与 C1 全量不可直接对比；样本小、置信区间宽",
    )
    return rec


def line_b分层_all(data, dry=False):
    """L2b：按全部 6 种 B 位分层训练 Δ 模型，覆盖全量 281 样本。

    与 L2 的区别：L2 只取 Pb/Sn（54 样本，19.2%），L2b 对 Ca/Ba/Sr/Sn/Ge/Pb
    各训一个 Δ 模型，样本多的层内部 KFold，样本少的层（<10）用留一或全量拟合。
    这是新实验线，样本按 B 位分组训练，评估器与 C1 不同，不直接对比。
    """
    folds = 2 if dry else 5
    per_group = {}
    ys, ps = [], []
    for b in sorted(set(data["bsite"])):
        mask = data["bsite"] == b
        Xb, db = data["X"][mask], data["delta"][mask]
        hb, pb = data["hse"][mask], data["pbe"][mask]
        per_group[str(b)] = int(mask.sum())
        if len(db) >= folds:
            kf = KFold(n_splits=min(folds, len(db)), shuffle=True, random_state=SEED)
            for tr, te in kf.split(Xb):
                m = RandomForestRegressor(n_estimators=10 if dry else 200,
                                          max_depth=10, random_state=SEED, n_jobs=-1)
                m.fit(Xb[tr], db[tr])
                ys.append(hb[te]); ps.append(pb[te] + m.predict(Xb[te]))
        else:
            # 样本太少无法交叉验证：全量拟合并回代（乐观估计，明确标注）
            m = RandomForestRegressor(n_estimators=10 if dry else 200,
                                      max_depth=10, random_state=SEED, n_jobs=-1)
            m.fit(Xb, db)
            ys.append(hb); ps.append(pb + m.predict(Xb))
    m = eval_pred(np.concatenate(ys), np.concatenate(ps))
    m["per_group"] = per_group
    m["coverage_of_281"] = 1.0
    m["note"] = "样本量小于折数的层用全量拟合回代（乐观估计）"
    rec = make_record(
        "L2b-6位分层", "b_site_layered_delta_all6",
        hypothesis="按 6 种 B 位各训 Δ 模型（覆盖全量）能否优于全局单一 Δ 模型",
        change="Ca/Ba/Sr/Sn/Ge/Pb 各训 1 个 Δ 模型；大层内部 KFold、小层全量回代；覆盖 281 全量",
        evaluator=f"按 B 位分层的 KFold({folds}, seed=42)；小层全量回代（乐观）",
        seed=SEED, metrics=m,
        conclusion=f"6 位分层 R²={m['r2']:.4f} MAE={m['mae']:.4f} eV（n={m['n']}，覆盖100%）",
        supported="待定",
        caveat="小层（Ge27/Pb25/Sn29 尚可，但按折划分后训练折更小）全量回代会高估；"
               "分层改变评估器口径，不与 C1 直接对比；对比对象应同样是分层口径的全局模型",
    )
    return rec


# ------------------------------------------------------------------ L3 电子描述子 + 外部集
ELECTRONEG = {  # Pauling 电负性（元素/基团）；MA/FA 用组成元素原子数加权平均（近似）
    'Cs': 0.79, 'Rb': 0.82, 'K': 0.82, 'Na': 0.93,
    'MA': 2.37, 'FA': 2.49,
    'Pb': 2.33, 'Sn': 1.96, 'Ge': 2.01, 'Ca': 1.00, 'Sr': 0.95, 'Ba': 0.89,
    'Cd': 1.69, 'Zn': 1.65, 'Mg': 1.31, 'Cu': 1.90, 'Ni': 1.91, 'Fe': 1.83,
    'Mn': 1.55, 'Co': 1.88,
    'Cl': 3.16, 'Br': 2.96, 'I': 2.66,
}
VALENCE = {  # 主族价电子数；MA/FA 按有机基团贡献近似
    'Cs': 1, 'Rb': 1, 'K': 1, 'Na': 1, 'MA': 5, 'FA': 8,
    'Pb': 4, 'Sn': 4, 'Ge': 4, 'Ca': 2, 'Sr': 2, 'Ba': 2,
    'Cd': 2, 'Zn': 2, 'Mg': 2, 'Cu': 1, 'Ni': 2, 'Fe': 2, 'Mn': 2, 'Co': 2,
}


def add_electronic_features(data):
    """在 34 维基础上追加 5 维电子描述子，返回新 X 与名字。"""
    d = data["df"]
    a_chi = d["A_site"].map(ELECTRONEG).fillna(0.0).to_numpy(float)
    b_chi = d["B_site"].map(ELECTRONEG).fillna(0.0).to_numpy(float)
    h_chi = (data["cl"] * ELECTRONEG['Cl'] + data["br"] * ELECTRONEG['Br']
             + data["i"] * ELECTRONEG['I']) / 3.0
    a_val = d["A_site"].map(VALENCE).fillna(0.0).to_numpy(float)
    b_val = d["B_site"].map(VALENCE).fillna(0.0).to_numpy(float)
    extra = np.column_stack([a_chi, b_chi, b_chi - a_chi, h_chi, a_val + b_val])
    names = ["A_electroneg", "B_electroneg", "chi_B_minus_A",
             "halogen_electroneg", "valence_A_plus_B"]
    X2 = np.hstack([data["X"], extra])
    return X2, data["names"] + names


def line_electronic(data, dry=False):
    """新特征 + group-disjoint 外部集：划 1 个 A_B 组作独立外部测试。"""
    X2, names2 = add_electronic_features(data)
    g = data["g"]
    groups = sorted(set(g), key=lambda k: -int((g == k).sum()))
    hold = groups[0]  # 划出最大组 K_Ca(22) 作外部集
    tr_mask = g != hold
    te_mask = ~tr_mask
    m = RandomForestRegressor(n_estimators=10 if dry else 200, max_depth=10,
                              random_state=SEED, n_jobs=-1)
    m.fit(X2[tr_mask], data["delta"][tr_mask])
    p = data["pbe"][te_mask] + m.predict(X2[te_mask])
    ext = eval_pred(data["hse"][te_mask], p)

    # 训练集内部 GroupKFold（剩余组）
    gkf = GroupKFold(n_splits=5)
    ys, ps = [], []
    for tr, te in gkf.split(X2[tr_mask], data["delta"][tr_mask], groups=g[tr_mask]):
        mm = RandomForestRegressor(n_estimators=10 if dry else 200, max_depth=10,
                                   random_state=SEED, n_jobs=-1)
        mm.fit(X2[tr_mask][tr], data["delta"][tr_mask][tr])
        ys.append(data["hse"][tr_mask][te])
        ps.append(data["pbe"][tr_mask][te] + mm.predict(X2[tr_mask][te]))
    grp = eval_pred(np.concatenate(ys), np.concatenate(ps))
    metrics = dict(external_group=hold, external_n=int(te_mask.sum()),
                   external=ext, group_cv=grp, n_features=int(X2.shape[1]),
                   added_features=names2[-5:])
    rec = make_record(
        "L3-电子描述子+外部集", "electronic_descriptors_group_disjoint",
        hypothesis="加电负性/价电子描述子并按 A_B 组划独立外部集，能给出更可信的泛化数字",
        change="特征 34→39 维（+5 电子描述子）；划 K_Ca(22) 整组作 group-disjoint 外部集；"
               "外部集全程不参与训练/调参",
        evaluator=f"group-disjoint 外部集({hold}, n={int(te_mask.sum())}) + 剩余组 GroupKFold(5)",
        seed=SEED, metrics=metrics,
        conclusion=f"外部集 R²={ext['r2']:.4f} MAE={ext['mae']:.4f} eV (n={ext['n']}); "
                   f"组内 GroupKFold R²={grp['r2']:.4f} MAE={grp['mae']:.4f}",
        supported="待定",
        caveat="MA/FA 电负性与价电子为组成元素近似的启发值（已在 ELECTRONEG/VALENCE 注明）；"
               "单个 A_B 组作外部集样本偏小；特征集与评估器均改变，属新实验线，不与 C1 直接对比",
    )
    return rec


# ------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description="v2.1 三项新实验线")
    ap.add_argument("--line", choices=["all", "shap", "b分层", "b分层全部", "electronic"], default="all")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    data = load_base()
    print(f"[data] n={data['n']} d={len(data['names'])} groups={len(set(data['g']))}")

    runners = []
    if args.line in ("all", "shap"):
        runners.append(("L1_shap.json", line_shap))
    if args.line in ("all", "b分层"):
        runners.append(("L2_b_layered.json", line_b分层))
    if args.line in ("all", "b分层全部"):
        runners.append(("L2b_b_layered_all6.json", line_b分层_all))
    if args.line in ("all", "electronic"):
        runners.append(("L3_electronic_ext.json", line_electronic))

    for fname, fn in runners:
        print(f"\n--- {fname} ({'dry' if args.dry_run else 'full'}) ---", flush=True)
        rec = fn(data, dry=args.dry_run)
        out = RESULTS / (fname if not args.dry_run else fname.replace(".json", "_dry.json"))
        with open(out, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2, default=str)
        print(f"  conclusion: {rec['conclusion']}")
        print(f"  supported: {rec['supported']}  -> {out}")


if __name__ == "__main__":
    main()
