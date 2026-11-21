# CHANGELOG

## v3.0.0 — 2026-11-21（全量重写研究内核）

按用户第三轮确认：完全按导师指导重构，R²为准/MAE上修，文献限优化方案附录B七条，网盘只替换重写文件。

### 结构性变更
- 新增 `src/`（data/models/evaluation/interpretation/active/api）+ `scripts/`（train/audit/interpret/active/serve）
  + `configs/`（超参数外置，extends 深合并）+ `docs/`（方法/文献/决策/验收）+ `data/raw/`（只读数据）。
- 历史 v2.x `backend/`、`frontend/` 保留供对照；v3 API 薄层复用 src 内核。

### 验收线（DEC-v3-001）
- 导师原 MAE 0.10–0.14 与 R² 0.90–0.94 在 std=1.4746 上不自洽（三处文档记录、导师未答）。
- 决策：R² 沿用，MAE 按 MAE≈0.7979·std·√(1−R²) 上修（随机 0.29–0.37 等），见 `docs/acceptance.md`。

### 五步路线落地
- 第0步：`src/data/cleaner.py` + `scripts/audit.py`（3σ 候选 0、τ 异常 4、is_converged 占位）。
- 第1步：`src/data/dataset.py::grid_weights`（C2 负面结果如实保留）。
- 第2步：`src/evaluation/`（三套验证 + 4 类诊断图 + 上修验收判定）。
- 第3步：`src/active/candidate.py`（LatinHypercube + 不确定性筛选，目标窗口候选 0 如实记录）。
- 第4步：`configs/base.json::evaluation.external`（group-disjoint 划组，非独立数据源）。

### 文献
- `docs/references.md` 仅列优化方案附录 B 七条已核验条目（DOI/PMID 原样），未新增任何文献。

### 验证
- 数据层 281/34 维（电子版 39 维）、训练入口 dry-run 字段完整、API 五路由 200、
  SHAP/主动学习跑通。正式三套验证结果见 `experiments/results/v3_*.json`。

## v2.1.1 — 2026-11-21（未提交，工作分支 improvement/global-refactor-v2.1）

按用户第二轮确认：API 输入改造（F6 处置）、L2b 六位分层、前端 dist 重建、按导师方案补齐工程。

### API 输入改造（处置 F6：模型重度依赖结构描述子）

| 文件 | 变更点 |
|---|---|
| `backend/app.py` | 新增 `STRUCTURE_PARAM_MAP`（8 个 API 短参数名 → 结构列名）与 `structure_values_from_request()`；`/api/predict`、`/api/predict/batch` 优先用请求传入的真实结构描述子，缺省回退训练均值；返回 `structure_source`（provided/default_mean）；新增 `GET /api/structure-defaults` |
| `frontend/src/pages/prediction/prediction.vue` | 新增"高级选项：结构描述子"折叠区（8 个 number 输入，默认值来自后端）；predict 仅发送与默认值不同的项；结果区显示均值填充提示 |
| `frontend/src/api/index.js` | 新增 `getStructureDefaults()` |
| `frontend/dist/` | `npm run build` 重建（旧构建产物已由新构建替换） |

验证：提供结构参数后预测值变化 0.0218 eV；`/api/structure-defaults` 返回 8 字段；全路由冒烟 200。

### 新实验线

| 实验ID | 结果 | 结论 |
|---|---|---|
| L2b-6位分层 | R²0.9395 / MAE0.2562 eV（n=281，覆盖100%） | 待定；小层全量回代偏乐观，不与 C1 直接对比 |
| （L1/L2/L3 见 v2.1.0） | | |

### 导师方案补齐工程（新增 `experiments/scripts/mentor_pipeline.py`）

- 第0步 标签校验：Δ 按 6 种 B 位分层 3σ 候选 **0 个**；τ 异常 **4 个**（τ<0.4 或 >1.1，只标不删）；`is_converged=unknown` 占位。产出 `QC0_label_audit.json`、`pending_review_outliers.csv`。
- 第2步 诊断图：4 张（预测散点、残差、三元卤素 MAE 热图、不确定性-误差）→ `experiments/figures/`。
- 第3步 主动学习队列：LatinHypercube 采样 2000 → 不确定性 Top30 → `active_learning_queue.csv`。目标带隙 1.3–1.5 eV 窗口内候选 **0 个**（HSE 用 PBE 均值近似导致普遍偏高，已如实记录）；目标窗口作加分项而非硬门限。
- 所有产出标注近似与局限，不改冻结评估器。

## v2.1.0 — 2026-11-21（未提交，工作分支 improvement/global-refactor-v2.1）

按用户确认执行：左侧 5 项更正 + 三项新实验线。所有新实验线均为独立线，
不改冻结的 C1 基线，标注 `comparable_to_C1_baseline=false`。

### 更正（5 项，不改评估器）

| 文件 | 变更点 |
|---|---|
| `backend/models/generator.py` | `_predict_bandgap()` 接回真实 Δ 预测器（此前始终返回启发式估计，`/api/generate` 绕过模型口径，见 MD-005 still_open#1）；依赖不全时回退启发式 |
| `backend/app.py` | 启动时用 `preprocessor.fit_structure_defaults()` 学习 8 个结构描述子的训练均值；predict/batch_predict 以均值替代硬编码 0.01；把 predictor/feature_engineer/defaults 传给 generator |
| `backend/data/preprocessor.py` | 新增 `STRUCTURE_COLS` 常量与 `fit_structure_defaults()` |
| `backend/requirements.txt` | 补 `scipy>=1.9.0`（generator/comparator 依赖，原清单缺失） |
| `backend/models/predictor.py` | 修正头部 docstring（默认口径为 RandomForest，非 XGBoost） |
| `CLAUDE.md` | 空模板 → 真实架构/命令/口径/已知局限 |

**API 语义变化**：结构描述子默认值 0.01 → 训练集列均值（如 Bartel's T.F. 4.02、Octahedral F. 0.58），
`predicted_bandgap` 数值会变化；字段名不变，前端无需改。

### 基线复现（冻结评估器，C1 full）

| 场景 | 旧基线(v2.0) | 本轮复现 | 说明 |
|---|---|---|---|
| 随机10×5 端到端 | R²0.7481/MAE0.5453 | R²0.7483/MAE0.5450 | 一致 |
| 随机10×5 oracle | R²0.9377/MAE0.2761 | R²0.9377/MAE0.2759 | 一致 |
| GroupKFold 端到端 | R²0.7308/MAE0.5819 | R²0.7243/MAE0.5938 | sklearn 1.9 划分差异，属复现波动 |
| GroupKFold oracle | R²0.9227/MAE0.3122 | R²0.9161/MAE0.3267 | 同上 |

### 新实验线（新增 `experiments/scripts/new_lines.py`）

| 实验ID | 改了什么 → 预期 | 实测结果 | 结论 |
|---|---|---|---|
| L1-SHAP | 用 TreeExplainer 替代 impurity 重要度 → 物理可解释排序 | Top3 全为结构描述子（cubicity β/α、八面体因子） | 信息性；**暴露矛盾**：这些特征推理时只能均值填充，模型重度依赖拿不到的信息 |
| L2-B分层 | Pb/Sn 各训一个 Δ → 降低组内误差 | 子集 R²0.6920/MAE0.3740（n=54） | 待定；仅覆盖 54/281(19.2%)，B 位实为 6 种（Ca/Ba/Sr/Sn/Ge/Pb），样本小置信宽 |
| L3-电子描述子+外部集 | +5 维电负性/价电子 + 划 K_Ca 整组作外部集 → 更可信泛化 | 外部 R²0.9563/MAE0.2367(n=22)；组内 GroupKFold R²0.9230/MAE0.3103 | 待定；MA/FA 电子参数为近似启发值，单组外部集偏小；特征+评估器双改变，不与 C1 对比 |

实验记录字段完整（`experiments/results/L1_shap.json` 等）：实验ID/配置hash/代码commit(+dirty)/
数据集/seed/指标/结论/supported/new_line/comparable_to_C1_baseline。

### 验证命令

```bash
cd backend
python -m py_compile app.py train.py data/preprocessor.py data/feature_engineer.py \
    models/predictor.py models/generator.py analysis/comparator.py
python train.py --check-shapes
python train.py --config C1 --dry-run
python train.py --config C1 --full
cd .. && python experiments/scripts/new_lines.py --line all --dry-run
python experiments/scripts/new_lines.py --line all
```

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
