# 钙钛矿带隙预测系统 — v3 研究内核

基于机器学习的钙钛矿带隙预测：由组分（A/B 位 + Cl/Br/I 比例）预测 HSErel_SOC 带隙，
采用 Δ-learning（PBE 基线 + Δ 修正）双模型，按导师五步路线组织研究内核。

## 版本沿革

- v1.0 / v2.0： Flask API + Vue 前端，Δ-learning 双模型（历史资产见网盘「毕设用」）。
- v2.1：5 项核心更正 + API 结构描述子入参 + 导师方案实验线（分支 `improvement/global-refactor-v2.1`）。
- **v3（本版）**：按导师五步路线全量重写研究内核，config 驱动，目录约定统一，
  验收线按 DEC-v3-001 上修。文献严格限于 `docs/references.md` 七条已核验条目。

## 快速开始

```bash
cd repo
pip install -r requirements.txt            # 含 scipy / shap / matplotlib
python scripts/audit.py                    # 第0步 标签审计
python scripts/train.py --config c1_delta_rf.json --dry-run   # 链路验证
python scripts/train.py --config c1_delta_rf.json             # 正式三套验证
python scripts/train.py --config c3_electronic_external.json  # 新实验线
python scripts/layered.py                      # B位分层 Δ 模型
python scripts/interpret.py                # SHAP 解释
python scripts/active.py                   # 主动学习 DFT 队列
python scripts/serve.py                    # API :5000
```

## 目录结构

```
configs/            实验配置（超参数外置）
data/raw/           只读原始数据 perovs_data_final.xlsx
src/data/           加载/清洗/预处理/电子描述子/数据集组装
src/models/         Δ双模型 / B位分层
src/evaluation/     三套验证 / 指标与验收判定 / 诊断图
src/interpretation/ SHAP
src/active/         主动学习候选队列
src/api/            Flask 薄层 + 推理封装
scripts/            train / audit / interpret / active / serve
experiments/        results / figures / 队列
docs/               方法 / 文献 / 决策 / 验收口径
tests/              测试
```

## 模型与口径

- 模型：两个 RandomForest（PBE 基线 488 样本 + Δ 模型 281 配对样本），n_estimators=200, max_depth=10, seed=42。
- 特征：基础 34 维（A/B one-hot + 卤素比例 + 离子半径 + 8 结构描述子）；可选 +5 维电子描述子。
- 口径：
  - end_to_end = PBE_pred + Δ_pred（主指标，仅组分，API 默认）；
  - oracle_pbe = PBE_true + Δ_pred（已有 PBE 结果时）。
  - 两口径不可混用；对外引用必须注明。
- 验收线：R² 沿用导师区间，MAE 按 std=1.4746 eV 上修，详见 `docs/acceptance.md`（DEC-v3-001）。

## API（主要路由）

| 路由 | 说明 |
|---|---|
| `GET /api/health` | 健康检查 |
| `GET /api/structure-defaults` | 8 个结构描述子的参数名/标签/训练均值 |
| `GET /api/elements` | 可用 A/B 位与卤素 |
| `POST /api/predict` | 单条预测（可传 8 结构描述子 + 可选 pbe_bandgap） |
| `POST /api/predict/batch` | 批量预测 |
| `GET /api/metrics` | 离线三套验证结果 |

`predicted_bandgap` 语义为 HSErel_SOC（比 PBE 高约 0.8 eV），字段名保持不变。
传入真实结构描述子时返回 `structure_source=provided`，否则 `default_mean`。

## 依赖与限制

- 环境：Python 3.8+；依赖见 `requirements.txt`。
- 已知局限：结构描述子推理时依赖填充；严格三元样本 0；B 位 6 种（Pb/Sn 分层仅覆盖 19.2%）；
  外部集为 group-disjoint 划组非独立数据源；MA/FA 电子参数为近似值。详见 `docs/methods.md`。
- 文献：`docs/references.md`（仅 7 条已核验条目，未新增）。

## Git 提交规范

feat / fix / docs / style / refactor / test / chore。
