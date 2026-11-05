#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/train.py — 项目正式离线训练与三套验证（v2.0）

与 /workspace/experiments/train_delta.py（最小骨架）的区别：
  * 骨架口径是 HSE = PBE_true + Δ_pred，PBE 用测试折真值加回，属"Δ 模型上限"评估；
  * 本脚本同时输出两个口径，对应两个真实的部署场景：
      - oracle_pbe（场景 A）：调用方已有便宜的 PBE 计算结果，只需估 HSE+SOC。
        这是 Δ-learning 在材料信息学里的标准用法，误差只来自 Δ 模型。
      - end_to_end（场景 B）：只有组分、没有任何 DFT 结果，PBE 也由模型预测。
        这是当前 Web API 的默认场景，PBE 模型的误差会叠加进来。
    PBE 模型在每一折的训练集上重新拟合（非配对 207 + 配对训练折），
    不泄露测试折的 PBE 标签。两者差距必须如实报告，不可混用。

三套验证（导师文档3）：
  random_cv      : RepeatedKFold(5, 10)        分布内插值
  group_cv       : GroupKFold(5, groups=A_B)  全新 A/B 外推
  external_proxy : GroupShuffleSplit(20%)     代理外部集，--external 开启，
                   非独立数据源，禁止写进论文主结论

命令：
  python backend/train.py --check-shapes
  python backend/train.py --config C1 --dry-run
  python backend/train.py --config C1 --full
  python backend/train.py --config C1 --full --external --out experiments/results/latest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, RepeatedKFold

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data.preprocessor import PerovskitePreprocessor  # noqa: E402
from data.feature_engineer import FeatureEngineer  # noqa: E402
from models.predictor import BandGapPredictor  # noqa: E402

DATA = ROOT / "d3dd00015j2" / "perovs_data_final.xlsx"
RESULTS = ROOT / "experiments" / "results"
SEED = 42

STRUCT_COLS = [
    'Deviation of Cubicity b axis', 'Deviation of Cubicity c axis',
    'Deviation of Cubicity at alpha', 'Deviation of Cubicity at beta',
    'Deviation of Cubicity at gamma', 'Octaehdral Factor',
    'Tolerance Factor', "Bartel's Tolerance Factor",
]

CONFIGS = {
    # 对照：故意丢掉 8 个结构描述子，复现 v3.0 的 26 维基线
    "C0": dict(drop_structure_cols=True, qc=False, model="random_forest", weighted=False),
    # 正式：完整 34 维 + Δ-learning
    "C1": dict(drop_structure_cols=False, qc=False, model="random_forest", weighted=False),
    # 导师方案组合：34 维 + 卤素网格加权 + XGB
    "C2": dict(drop_structure_cols=False, qc=True, model="xgboost", weighted=True),
}


# ------------------------------------------------------------------ 数据
def load_data(cfg):
    """数据加载与特征构造。

    in : cfg(dict)
    out: dict{
      X_pair (n_pair,d), X_unpair (n_unpair,d), y_pbe_pair (n_pair,),
      y_hse (n_pair,), y_unpair (n_unpair,), delta (n_pair,),
      g (n_pair,) object, cl_raw/br_raw (n_pair,), names (d,)
    }
    n_pair=281, n_unpair=207, d=34（C0 为 26）
    """
    if not DATA.exists():
        raise FileNotFoundError(f"数据文件不存在：{DATA}")
    pbe = pd.read_excel(DATA, sheet_name="PBE")             # (488, 12)
    hse = pd.read_excel(DATA, sheet_name="HSErel_SOC")      # (282, 4)
    if not hse["Formula"].is_unique or not pbe["Formula"].is_unique:
        raise ValueError("Formula 不唯一，Δ 标签配对不可靠")

    prep = PerovskitePreprocessor()
    parsed = prep.extract_features(pbe)                     # (488, 12+6)

    n_dropped = 0
    if cfg["qc"]:
        ok = parsed["A_site"].notna() & parsed["B_site"].notna()
        n_dropped = int((~ok).sum())
        pbe, parsed = pbe.loc[ok].reset_index(drop=True), parsed.loc[ok].reset_index(drop=True)

    # C0 对照：删掉 8 个结构描述子，模拟"merge 只取 3 列"造成的特征坍塌
    if cfg["drop_structure_cols"]:
        parsed = parsed.drop(columns=STRUCT_COLS, errors="ignore")

    X_all, _, names = prep.create_feature_matrix(parsed, include_target=False)  # (488, d)
    X_all = np.nan_to_num(np.asarray(X_all, dtype=np.float64),
                          nan=0.0, posinf=0.0, neginf=0.0)
    y_all = pbe["Band Gap (eV)"].to_numpy(np.float64)     # (488,) PBE 标签

    # 以 PBE 全量列构造特征，不做 merge 截断，因此 34 维描述子完整保留。
    hse_map = hse.set_index("Formula")["Band Gap (eV)"]
    pair_mask = pbe["Formula"].isin(hse_map.index).to_numpy()   # (488,) bool
    y_hse = pbe.loc[pair_mask, "Formula"].map(hse_map).to_numpy(np.float64)  # (281,)
    y_pbe_pair = y_all[pair_mask]                         # (281,)
    delta = y_hse - y_pbe_pair                           # (281,)

    # 树模型对单调线性缩放不敏感（实测前后预测差 8.9e-16），全局 fit
    # 不构成实质泄露；换线性/NN 模型时必须改为折内 fit。
    X_all_s = FeatureEngineer().fit_transform(X_all, names)     # (488, d)
    X_pair, X_unpair = X_all_s[pair_mask], X_all_s[~pair_mask]
    y_unpair = y_all[~pair_mask]                          # (207,)

    # dtype=object 必须保留：numpy str dtype 会被 sklearn check_array
    # 尝试转 float，导致 GroupKFold 报 "Input contains NaN"。
    g_all = np.array(
        [f"{a}_{b}" for a, b in zip(parsed["A_site"], parsed["B_site"])],
        dtype=object,
    )
    g = g_all[pair_mask]                                  # (281,)
    cl_raw = parsed["Cl_ratio"].to_numpy(np.float64)[pair_mask]   # (281,)
    br_raw = parsed["Br_ratio"].to_numpy(np.float64)[pair_mask]   # (281,)

    n_pair = len(y_hse)
    assert X_pair.shape == (n_pair, len(names)), "配对特征形状错误"
    assert X_unpair.shape[0] == len(y_unpair), "非配对特征形状错误"
    assert delta.shape == y_pbe_pair.shape == g.shape == (n_pair,), "标签形状错误"
    assert np.isfinite(X_pair).all() and np.isfinite(delta).all(), "不得含 NaN/Inf"
    return dict(
        X_pair=X_pair, X_unpair=X_unpair, y_pbe_pair=y_pbe_pair,
        y_hse=y_hse, y_unpair=y_unpair, delta=delta, g=g,
        cl_raw=cl_raw, br_raw=br_raw, names=list(names),
        n_pair=n_pair, n_unpair=len(y_unpair), d=len(names),
        n_dropped=n_dropped, groups=len(set(g)),
    )


def grid_weights(data):
    """导师文档3 方案1：卤素 10x10 网格密度倒数权重。in: data -> out: w(n_pair,)。"""
    bx = np.clip((data["cl_raw"] / 3.0 * 10).astype(int), 0, 9)
    by = np.clip((data["br_raw"] / 3.0 * 10).astype(int), 0, 9)
    cnt = np.zeros((10, 10), dtype=np.float64)
    for a, b in zip(bx, by):
        cnt[a, b] += 1
    w = np.array([1.0 / max(cnt[a, b], 1.0) for a, b in zip(bx, by)])
    return w / w.mean()


# ------------------------------------------------------------------ 训练与评估
def evaluate(y_true, y_pred):
    """in: y_true(n,), y_pred(n,) -> out: dict{r2,mae,rmse,n}"""
    assert y_true.shape == y_pred.shape and y_true.ndim == 1
    return dict(
        r2=float(r2_score(y_true, y_pred)),
        mae=float(mean_absolute_error(y_true, y_pred)),
        rmse=float(np.sqrt(mean_squared_error(y_true, y_pred))),
        n=int(len(y_true)),
    )


def fit_fold(data, cfg, tr, te, n_estimators, w=None):
    """单折训练。in: tr(n_tr,), te(n_te,) 索引 -> out: (pbe_pred(n_te,), d_pred(n_te,))。

    严格无泄露：PBE 模型的训练集 = 207 个非配对样本 + 配对样本中的 tr，
    不含测试折 te 的 PBE 标签；Δ 模型只在配对样本 tr 上训练。
    """
    X_pbe_tr = np.vstack([data["X_unpair"], data["X_pair"][tr]])       # (n_unpair+n_tr, d)
    y_pbe_tr = np.concatenate([data["y_unpair"], data["y_pbe_pair"][tr]])
    pbe_m = BandGapPredictor(model_type=cfg["model"])
    pbe_m.train(X_pbe_tr, y_pbe_tr, feature_names=data["names"],
                n_estimators=n_estimators, compute_cv=False)

    d_m = BandGapPredictor(model_type=cfg["model"])
    d_m.train(data["X_pair"][tr], data["delta"][tr], feature_names=data["names"],
              n_estimators=n_estimators, compute_cv=False,
              sample_weight=w[tr] if w is not None else None)

    pbe_pred = pbe_m.predict(data["X_pair"][te])                        # (n_te,)
    d_pred = d_m.predict(data["X_pair"][te])                            # (n_te,)
    assert pbe_pred.shape == d_pred.shape == (len(te),)
    return pbe_pred, d_pred


def run_split(data, cfg, splitter, n_estimators, w=None, max_folds=None):
    """逐折训练并拼接预测，同时给出两个口径。out: dict。"""
    ys, ps_oracle, ps_e2e, nfold = [], [], [], 0
    for tr, te in splitter:
        pbe_pred, d_pred = fit_fold(data, cfg, tr, te, n_estimators, w)
        ys.append(data["y_hse"][te])
        ps_oracle.append(data["y_pbe_pair"][te] + d_pred)   # v3.0 对账口径
        ps_e2e.append(pbe_pred + d_pred)                    # 实际推理口径（主指标）
        nfold += 1
        if max_folds and nfold >= max_folds:
            break
    y = np.concatenate(ys)
    return dict(
        end_to_end=evaluate(y, np.concatenate(ps_e2e)),
        oracle_pbe=evaluate(y, np.concatenate(ps_oracle)),
        folds=nfold,
    )


def run(data, cfg, dry=False, external=False):
    """三套验证。in: data, cfg, dry, external -> out: dict。"""
    n_estimators = 10 if dry else 200
    n_repeats = 1 if dry else 10
    w = grid_weights(data) if cfg["weighted"] else None
    max_folds = 1 if dry else None

    result = dict(
        config=cfg, n_pair=data["n_pair"], n_unpair=data["n_unpair"],
        d=data["d"], groups=data["groups"], n_dropped_by_qc=data["n_dropped"],
        n_estimators=n_estimators, n_repeats=n_repeats, seed=SEED,
        basis="end_to_end = PBE_pred + Δ_pred（场景B：仅组分输入，API 默认）；"
              "oracle_pbe = PBE_true + Δ_pred（场景A：已有 PBE 计算结果）",
    )

    rkf = RepeatedKFold(n_splits=5, n_repeats=n_repeats, random_state=SEED)
    result["random_cv"] = run_split(data, cfg, rkf.split(data["X_pair"]),
                                    n_estimators, w, max_folds)
    gkf = GroupKFold(n_splits=5)
    result["group_cv"] = run_split(
        data, cfg,
        gkf.split(data["X_pair"], data["delta"], groups=data["g"]),
        n_estimators, w, max_folds,
    )

    if external:
        gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
        tr, te = next(gss.split(data["X_pair"], data["delta"], groups=data["g"]))
        pbe_pred, d_pred = fit_fold(data, cfg, tr, te, n_estimators, w)
        result["external_proxy"] = dict(
            end_to_end=evaluate(data["y_hse"][te], pbe_pred + d_pred),
            oracle_pbe=evaluate(data["y_hse"][te], data["y_pbe_pair"][te] + d_pred),
            note="代理外部集，非独立数据源，不可作论文主结论",
        )
    return result


# ------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description="钙钛矿 Δ-learning 正式训练与三套验证")
    ap.add_argument("--config", choices=list(CONFIGS), default="C1")
    ap.add_argument("--check-shapes", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--external", action="store_true")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    if args.check_shapes:
        print("[check-shapes] 逐配置加载并校验形状契约")
        for name, cfg in CONFIGS.items():
            d = load_data(cfg)
            print(f"  {name}: X_pair={d['X_pair'].shape} X_unpair={d['X_unpair'].shape} "
                  f"delta={d['delta'].shape} g={d['g'].shape}({d['g'].dtype}) "
                  f"names={d['d']} groups={d['groups']} qc_dropped={d['n_dropped']}  [OK]")
        print("[check-shapes] 全部通过")
        return

    cfg = CONFIGS[args.config]
    mode = "dry-run" if args.dry_run else "full"
    data = load_data(cfg)
    print(f"[{mode}] config={args.config} X_pair={data['X_pair'].shape} "
          f"X_unpair={data['X_unpair'].shape} delta={data['delta'].shape} "
          f"n_estimators={10 if args.dry_run else 200} "
          f"n_repeats={1 if args.dry_run else 10}", flush=True)

    res = run(data, cfg, dry=args.dry_run, external=args.external)
    for key in ("random_cv", "group_cv"):
        b = res[key]
        e, o = b["end_to_end"], b["oracle_pbe"]
        print(f"  {key:12s} folds={b['folds']:2d} | 端到端 R2={e['r2']:.4f} MAE={e['mae']:.4f} "
              f"| oracle R2={o['r2']:.4f} MAE={o['mae']:.4f}")
    if "external_proxy" in res:
        e = res["external_proxy"]["end_to_end"]
        print(f"  external_proxy    | 端到端 R2={e['r2']:.4f} MAE={e['mae']:.4f} "
              f"(代理集，不作主结论)")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else RESULTS / "latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    with open(RESULTS / f"train_{args.config}.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"结果已写入 {out}")


if __name__ == "__main__":
    main()
