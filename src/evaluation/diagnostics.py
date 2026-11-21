"""四类诊断图（导师方案第2步，论文素材）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np


def make_diagnostics(y: np.ndarray, p: np.ndarray, cl: np.ndarray,
                     br: np.ndarray, uncertainty: np.ndarray,
                     out_dir: Path) -> Dict[str, str]:
    """生成 4 张诊断图，返回路径清单。in: 真值/预测/组分/不确定性/输出目录。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}
    err = p - y

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(y, p, s=12, alpha=0.6)
    lim = [float(min(y.min(), p.min())) - 0.2, float(max(y.max(), p.max())) + 0.2]
    ax.plot(lim, lim, "k--", lw=1)
    ax.set_xlabel("True HSErel_SOC (eV)"); ax.set_ylabel("Predicted (eV)")
    ax.set_title("Predicted vs True")
    fig.tight_layout(); f = out_dir / "01_pred_scatter.png"
    fig.savefig(f, dpi=120); plt.close(fig); paths["scatter"] = str(f)

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(p, err, s=12, alpha=0.6); ax.axhline(0, color="k", lw=1)
    ax.set_xlabel("Predicted (eV)"); ax.set_ylabel("Residual (eV)")
    ax.set_title("Residuals vs Predicted")
    fig.tight_layout(); f = out_dir / "02_residual.png"
    fig.savefig(f, dpi=120); plt.close(fig); paths["residual"] = str(f)

    bx = np.clip((cl / 3.0 * 10).astype(int), 0, 9)
    by = np.clip((br / 3.0 * 10).astype(int), 0, 9)
    heat = np.full((10, 10), np.nan)
    for a, b, e in zip(bx, by, np.abs(err)):
        v = float(e) if np.isnan(heat[a, b]) else float((heat[a, b] + abs(e)) / 2)
        heat[a, b] = v
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    im = ax.imshow(heat.T, origin="lower", cmap="YlOrRd", aspect="auto")
    ax.set_xlabel("Cl bin (0-3 → 0-9)"); ax.set_ylabel("Br bin (0-3 → 0-9)")
    ax.set_title("Halogen Ternary MAE Heatmap")
    fig.colorbar(im, ax=ax, label="|error| (eV)")
    fig.tight_layout(); f = out_dir / "03_halogen_mae_heatmap.png"
    fig.savefig(f, dpi=120); plt.close(fig); paths["heatmap"] = str(f)

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.scatter(uncertainty, np.abs(err), s=12, alpha=0.6)
    ax.set_xlabel("Tree-std uncertainty (eV)"); ax.set_ylabel("|residual| (eV)")
    ax.set_title("Uncertainty vs Error")
    fig.tight_layout(); f = out_dir / "04_uncertainty_error.png"
    fig.savefig(f, dpi=120); plt.close(fig); paths["uncertainty"] = str(f)
    return paths
