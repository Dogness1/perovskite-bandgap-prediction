# CHANGELOG

## v2.0.0 — 2026-11-05

按 `优化方案 v3.0`（指标对账与训练骨架）落地 P0-1 / P0-2，并补齐此前未报告的评估口径差异。

### 新增

| 文件 | 作用 |
|---|---|
| `backend/train.py` | 离线训练与三套验证：随机 `RepeatedKFold(5×10)`、`GroupKFold(5, groups=A_B)`、代理外部集；结果写入 `experiments/results/latest.json` |
| `GET /api/metrics` | 返回启动时的快速评估与 `train.py` 的完整结果 |
| `POST /api/predict` 可选参数 `pbe_bandgap` | 调用方已有 PBE 计算结果时直接作为基线（场景 A） |
| `CHANGELOG.md` | 本文件 |

### 修改

| 文件 | 变更点 |
|---|---|
| `backend/app.py` | 改为 PBE 基线模型 + Δ 模型的双模型口径；merge 保留 PBE 全量列（34 维）；新增 `DeltaCorrectedPredictor`；预测接口返回 PBE/Δ 分项；stats 增加配对样本数 |
| `backend/data/preprocessor.py` | `parse_formula()` 增加混合 A 位化学式的 B 位回退解析（修复 31 个样本的静默特征污染）；`avg_halogen_radius` 改按真实卤素总数加权 |
| `backend/models/predictor.py` | `train()` 增加 `sample_weight` / `cv_repeats` / `compute_cv`；`evaluate()` 增加 `groups` 分项 MAE |
| `README.md` | 修正模型、指标、目录名等过时声称；新增两种口径与训练校验命令 |
| `项目汇报SOP.md` | 修正 XGBoost / R²=0.87 / MAE=0.28 等过时声称，改为分场景实测值 |
| `frontend/src/pages/prediction/prediction.vue` | 标题与导出列头标注 HSErel_SOC 口径（仅源码，`dist/` 需重新构建） |

### 实测指标（`python backend/train.py --config C1 --full`）

| 场景 | 计算式 | 随机 10×5 CV | GroupKFold(5) |
|---|---|---|---|
| A：已有 PBE 结果 | PBE_true + Δ_pred | R² 0.9377 / MAE 0.2761 eV | R² 0.9227 / MAE 0.3122 eV |
| B：仅组分输入（API 默认） | PBE_pred + Δ_pred | R² 0.7481 / MAE 0.5453 eV | R² 0.7308 / MAE 0.5819 eV |

**这是本版最重要的修正**：此前报告的数字都属于场景 A（PBE 用测试折真值加回），而 Web API 实际运行在场景 B，PBE 模型的误差会叠加进来，MAE 约翻倍。两个口径不可混用，对外引用必须注明。

### 兼容性

- **接口字段不变**：`predicted_bandgap` 仍在，前端无需改动即可运行。
- **语义变化**：该字段的含义由 PBE 带隙改为 HSErel_SOC 带隙，数值整体上移约 0.8 eV。前端已加口径标注；`frontend/dist/` 为旧构建产物，需 `npm run build` 才会更新。
- 其余路由均通过冒烟测试（health / stats / distribution / elements / predict / batch / metrics / feature-importance / halogen-effect / generate / export）。

### 验证命令

```bash
cd backend
python -m py_compile app.py train.py data/preprocessor.py models/predictor.py
python -m pyflakes app.py train.py data/preprocessor.py models/predictor.py
python train.py --check-shapes
python train.py --config C1 --dry-run
python train.py --config C1 --full
```

### 待办（未纳入本版）

1. 独立外部测试集：当前 `--external` 只是从现有 281 个配对样本切出的代理集，不可作论文主结论。
2. Optuna 超参搜索：目标函数应设为 GroupKFold 的 MAE。
3. 前端重新构建，使 `dist/` 与源码口径标注一致。
4. 与导师核对验收表：MAE 0.10–0.14 eV 与 R² 0.90–0.94 在 std=1.4746 eV 的目标上数学上不自洽。
