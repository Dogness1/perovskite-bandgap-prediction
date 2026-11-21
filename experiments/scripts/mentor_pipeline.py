#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mentor_pipeline.py — 按优化方案 v2.0 五步路线补齐的增量工程（v2.1）

三块产出，均不改冻结的 C1 评估器、不改 backend 训练逻辑：
  [第0步] 标签配对校验：Δ 按 B 位分层的 3σ 逐出候选清单（只标不删）、
          is_converged 数据版本占位列声明、τ 异常标记。
  [第2步] 四类诊断图：预测散点、残差图、三元卤素 MAE 热图、不确定性-误差关联。
  [第3步] 主动学习候选队列：LatinHypercube 采样 + 不确定性/目标窗口/τ 筛选 → DFT 计算队列 CSV。

宪法约束：
  - 3.4 可归因；3.6 负面结果保留；5.1 不硬写结论；5.3 数字来自结构化记录。
  - 一切产出写入 experiments/，不改 data/（原始数据只读）。

命令：
  python experiments/scripts/mentor_pipeline.py --all
  python experiments/scripts/mentor_pipeline.py --step qc
  python experiments/scripts/mentor_pipeline.py --step figures
  python experiments/scripts/mentor_pipeline.py --step active
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "experiments" / "scripts"))
from new_lines import load_base, SEED, ELECTRONEG  # noqa: E402
from sklearn.ensemble import RandomForestRegressor  # noqa: E402

DATA = ROOT / "d3dd00015j2" / "perovs_data_final.xlsx"
OUT = ROOT / "experiments"
FIG = OUT / "figures"
RESULTS = OUT / "results"


# ------------------------------------------------------------------ 第0步 标签校验
def step_qc(data):
    """Δ 按 B 位分层统计 + 3σ 逐出候选（只标不删）+ τ/is_converged 占位。"""
    df = data["df"].copy()
    df["delta"] = data["delta"]

    # 按 B 位分层算 μ/σ，3σ 判异常（分层而非全局，避免误伤 Sn 基真实高 Δ）
    rows, candidates = [], []
    for b, grp in df.groupby("B_site"):
        mu, sd = grp["delta"].mean(), grp["delta"].std(ddof=1)
        lo, hi = mu - 3 * sd, mu + 3 * sd
        rows.append(dict(B_site=str(b), n=len(grp), delta_mean=float(mu),
                         delta_std=float(sd), low_3sigma=float(lo), high_3sigma=float(hi)))
        for idx, r in grp.iterrows():
            if r["delta"] < lo or r["delta"] > hi:
                candidates.append(dict(formula=str(r["Formula"]), B_site=str(b),
                                       delta=float(r["delta"]), layer_mean=float(mu),
                                       layer_std=float(sd),
                                       z_score=float((r["delta"] - mu) / sd),
                                       action="待人工回查，不自动删除"))

    # τ（容忍因子）异常标记：τ<0.4 或 >1.1
    tau = pd.to_numeric(df.get("Tolerance Factor", pd.Series([np.nan] * len(df))), errors="coerce")
    tau_flag = int(((tau < 0.4) | (tau > 1.1)).sum())

    # is_converged 占位（数据版本缺口：无法追溯上游 DFT 收敛参数）
    df["is_converged"] = "unknown"
    df["delta_zscore_by_B"] = df.apply(
        lambda r: (r["delta"] - df.loc[df["B_site"] == r["B_site"], "delta"].mean())
        / max(df.loc[df["B_site"] == r["B_site"], "delta"].std(ddof=1), 1e-9), axis=1)

    summary = dict(
        experiment_id="QC0-标签校验",
        paired_samples=int(len(df)),
        by_B_site=rows,
        outlier_3sigma_candidates=candidates,
        outlier_count=len(candidates),
        tau_anomaly_count=tau_flag,
        tau_rule="tau<0.4 or tau>1.1（标记不删除）",
        is_converged="unknown（数据版本已知缺口：无法核验各样本 DFT 收敛参数）",
        action_note="3σ 候选与 τ 异常均只标记、交人工/导师回查；禁止按残差删样本刷 R²",
    )
    RESULTS.mkdir(exist_ok=True, parents=True)
    with open(RESULTS / "QC0_label_audit.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    # 待回查清单 CSV
    pd.DataFrame(candidates).to_csv(OUT / "pending_review_outliers.csv",
                                    index=False, encoding="utf-8-sig") if candidates else None
    print(f"[第0步] B位 3σ 候选={len(candidates)}，τ异常={tau_flag}，is_converged=unknown")
    for c in candidates[:5]:
        print(f"    {c['formula']} B={c['B_site']} Δ={c['delta']:.3f} z={c['z_score']:.2f}")
    return summary


# ------------------------------------------------------------------ 第2步 诊断图
def step_figures(data):
    """四类诊断图。用 C1 口径 OOF 预测（逐折 PBE+Δ）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIG.mkdir(exist_ok=True, parents=True)
    from sklearn.model_selection import KFold, GroupKFold

    def oof(splitter):
        ys, ps, dlt = [], [], []
        for tr, te in splitter:
            m = RandomForestRegressor(n_estimators=200, max_depth=10,
                                      random_state=SEED, n_jobs=-1)
            m.fit(data["X"][tr], data["delta"][tr])
            dp = m.predict(data["X"][te])
            ys.append(data["hse"][te]); ps.append(data["pbe"][te] + dp); dlt.append(dp)
        return np.concatenate(ys), np.concatenate(ps), np.concatenate(dlt)

    y_r, p_r, _ = oof(KFold(5, shuffle=True, random_state=SEED).split(data["X"]))
    y_g, p_g, _ = oof(GroupKFold(5).split(data["X"], data["delta"], groups=data["g"]))

    # 图1 预测散点（随机/Group 双色 + y=x）
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(y_r, p_r, s=12, alpha=0.6, label=f"random KFold (n={len(y_r)})")
    ax.scatter(y_g, p_g, s=12, alpha=0.6, label=f"GroupKFold (n={len(y_g)})")
    lim = [min(y_r.min(), y_g.min()) - 0.2, max(y_r.max(), y_g.max()) + 0.2]
    ax.plot(lim, lim, "k--", lw=1)
    ax.set_xlabel("True HSErel_SOC (eV)"); ax.set_ylabel("Predicted (eV)")
    ax.set_title("Predicted vs True"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "01_pred_scatter.png", dpi=120); plt.close(fig)

    # 图2 残差 vs 预测带隙
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(p_r, p_r - y_r, s=12, alpha=0.6)
    ax.axhline(0, color="k", lw=1)
    ax.set_xlabel("Predicted (eV)"); ax.set_ylabel("Residual (eV)")
    ax.set_title("Residuals vs Predicted")
    fig.tight_layout(); fig.savefig(FIG / "02_residual.png", dpi=120); plt.close(fig)

    # 图3 三元卤素 MAE 热图（Cl-Bi 平面，I=3-Cl-Br 由约束定）
    cl, br = data["cl"], data["br"]
    bx = np.clip((cl / 3.0 * 10).astype(int), 0, 9)
    by = np.clip((br / 3.0 * 10).astype(int), 0, 9)
    err = np.abs(p_r - y_r)
    heat = np.full((10, 10), np.nan)
    for a, b, e in zip(bx, by, err):
        heat[a, b] = e if np.isnan(heat[a, b]) else (heat[a, b] + e) / 2
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    im = ax.imshow(heat.T, origin="lower", cmap="YlOrRd", aspect="auto")
    ax.set_xlabel("Cl bin (0-3 -> 0-9)"); ax.set_ylabel("Br bin (0-3 -> 0-9)")
    ax.set_title("Halogen Ternary MAE Heatmap")
    fig.colorbar(im, ax=ax, label="MAE (eV)")
    fig.tight_layout(); fig.savefig(FIG / "03_halogen_mae_heatmap.png", dpi=120); plt.close(fig)

    # 图4 不确定性-误差关联（树间标准差 vs 绝对误差）
    m = RandomForestRegressor(n_estimators=200, max_depth=10,
                              random_state=SEED, n_jobs=-1)
    m.fit(data["X"], data["delta"])
    std = np.std([t.predict(data["X"]) for t in m.estimators_], axis=0)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(std, err, s=12, alpha=0.6)
    ax.set_xlabel("Tree-std uncertainty (eV)"); ax.set_ylabel("|residual| (eV)")
    ax.set_title("Uncertainty vs Error")
    fig.tight_layout(); fig.savefig(FIG / "04_uncertainty_error.png", dpi=120); plt.close(fig)

    manifest = dict(experiment_id="FIG-diagnostics", figures=[
        str(FIG / "01_pred_scatter.png"), str(FIG / "02_residual.png"),
        str(FIG / "03_halogen_mae_heatmap.png"), str(FIG / "04_uncertainty_error.png")],
        basis="C1 口径 OOF（random KFold / GroupKFold），200 trees，seed=42",
        note="诊断图是论文素材，不产出新精度结论")
    with open(RESULTS / "FIG_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[第2步] 生成 4 张诊断图 -> {FIG}")
    return manifest


# ------------------------------------------------------------------ 第3步 主动学习候选
def step_active(data, n_candidates=2000):
    """拉丁超立方采样 A/B/Cl/Br/I，筛选高不确定性 + 目标带隙 + τ 稳定 → DFT 队列。"""
    A_SITES = ["MA", "FA", "Cs", "Rb", "K", "Na"]
    B_SITES = ["Ca", "Ba", "Sr", "Sn", "Ge", "Pb"]
    sampler = qmc.LatinHypercube(d=3, seed=SEED)
    u = sampler.random(n=n_candidates)
    cl = u[:, 0] * 3
    br = u[:, 1] * (3 - cl)
    i = 3 - cl - br
    a_idx = np.random.default_rng(SEED).integers(0, len(A_SITES), n_candidates)
    b_idx = np.random.default_rng(SEED + 1).integers(0, len(B_SITES), n_candidates)

    # 用训练好的 Δ 模型估计带隙与不确定性（与候选特征同为 34 维基础口径）
    m = RandomForestRegressor(n_estimators=200, max_depth=10,
                              random_state=SEED, n_jobs=-1)
    m.fit(data["X"], data["delta"])
    # 候选特征：复用训练集均值行 + 替换 A/B onehot 与卤素（近似筛选，非最终 DFT）
    base = data["X"].mean(axis=0)
    cand_X = np.tile(base, (n_candidates, 1))
    names = data["names"]
    for k, site in enumerate(A_SITES):
        col = names.index(f"A_{site}") if f"A_{site}" in names else None
        if col is not None:
            cand_X[:, col] = (a_idx == k).astype(float)
    for k, site in enumerate(B_SITES):
        col = names.index(f"B_{site}") if f"B_{site}" in names else None
        if col is not None:
            cand_X[:, col] = (b_idx == k).astype(float)
    for nm, vals in (("Cl_ratio", cl), ("Br_ratio", br), ("I_ratio", i)):
        if nm in names:
            cand_X[:, names.index(nm)] = vals
    dp = m.predict(cand_X)
    std = np.std([t.predict(cand_X) for t in m.estimators_], axis=0)
    # PBE 基线用训练均值近似 → HSE 估计（筛选用途，非最终预测）
    hse_est = data["pbe"].mean() + dp
    # τ 近似：用数据集容忍因子均值附近筛选（精确 τ 需结构）
    tau_mean = float(pd.to_numeric(data["df"].get("Tolerance Factor"), errors="coerce").mean())

    # 主筛选：不确定性 Top-N；目标带隙 1.3-1.5 eV 作为优先级加分而非硬门限
    # （硬 AND 在实测中选中 0 个，因 PBE 均值近似使 HSE 估计普遍偏高）
    in_window = (hse_est >= 1.3) & (hse_est <= 1.5)
    score = std + 0.1 * in_window.astype(float)  # 窗口内加 0.1 分优先
    sel = np.argsort(-score)[:30]
    n_in_window = int(in_window[sel].sum())

    queue = pd.DataFrame({
        "rank": range(1, len(sel) + 1),
        "A_site": [A_SITES[a_idx[j]] for j in sel],
        "B_site": [B_SITES[b_idx[j]] for j in sel],
        "Cl": np.round(cl[sel], 3), "Br": np.round(br[sel], 3), "I": np.round(i[sel], 3),
        "hse_est_ev": np.round(hse_est[sel], 3),
        "uncertainty_ev": np.round(std[sel], 3),
        "tau_estimate": round(tau_mean, 3),
        "in_target_window": ["yes" if (1.3 <= h <= 1.5) else "no" for h in hse_est[sel]],
        "priority_note": "按不确定性降序；目标带隙窗口作加分；τ 与 HSE 均为近似，需 DFT 精算",
    })
    queue.to_csv(OUT / "active_learning_queue.csv", index=False, encoding="utf-8-sig")
    summary = dict(experiment_id="AL-候选队列", n_candidates=int(n_candidates),
                   n_selected=int(len(sel)), n_in_target_window=n_in_window,
                   selection_rule="不确定性 Top30；目标带隙 1.3-1.5 eV 作加分项（非硬门限）",
                   caveat="候选特征用训练集均值行近似（结构描述子不可得）；hse_est 用 PBE 均值近似，"
                          "导致落入目标窗口的候选很少；本队列仅供 DFT 计算排序，不构成精度结论；τ 需 DFT 精算")
    with open(RESULTS / "AL_queue_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[第3步] 候选 {n_candidates} → 选中 {len(sel)} → {OUT / 'active_learning_queue.csv'}")
    return summary


def main():
    ap = argparse.ArgumentParser(description="导师方案增量工程")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--step", choices=["qc", "figures", "active"], default=None)
    args = ap.parse_args()
    steps = ["qc", "figures", "active"] if (args.all or not args.step) else [args.step]
    data = load_base()
    print(f"[data] n={data['n']} d={len(data['names'])}")
    for s in steps:
        {"qc": step_qc, "figures": step_figures, "active": step_active}[s](data)


if __name__ == "__main__":
    main()
