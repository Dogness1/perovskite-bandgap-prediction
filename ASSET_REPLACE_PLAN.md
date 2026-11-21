# 网盘「毕设用」资产替换清单（v3）

> 策略（用户 DEC-v3-003）：**只替换重写的文件**，历史版本与依据文档保留。
> 流程：本清单先展示变更 → 用户确认 → 再上传（review-before-upload）。

## A. 建议替换（本轮已重写，内容完全更新）

| 网盘旧资产 | 本地新文件 | 变更摘要 |
|---|---|---|
| `README.md`（7.3KB） | `README.md` | v1/v2 旧声称 → v3 研究内核：新目录、config 驱动、验收口径、API |
| `CLAUDE.md`（386B） | `CLAUDE.md` | 从空模板「这是空项目工作区」→ 真实架构/命令/口径/局限 |
| `CHANGELOG.md`（3.4KB） | `CHANGELOG.md` | 追加 v3.0.0 全量重写记录（保留 v2.1/v2.0 历史条目） |
| `requirements`（124B） | `requirements.txt` | 补 scipy/shap/matplotlib，独立成根目录依赖 |
| `train_delta.py`（14KB） | `scripts/train.py` + `src/` | 最小骨架 → v3 完整内核（config 驱动、三套验证、验收判定、完整实验记录） |

## B. 建议保留（依据文档 / 历史决策，不覆盖）

| 网盘资产 | 保留理由 |
|---|---|
| `优化方案_v1.0/v2.0`（md/docx） | 导师五步路线的依据来源，文献即取自其附录B |
| `指标对账与训练骨架_v3.0`（md/docx） | 验收线矛盾推导的 provenance，引用来源不能覆盖 |
| `decision_MD-003/004/005.json` | 历史决策记录（宪法 1.3 状态以结构化记录为准） |
| `文献核验与数据集优化方向报告_v1`（docx） | 文献核验历史 |
| `项目汇报SOP`、`零基础上手指引` | 汇报/上手材料，非本轮重写对象 |
| `perovskite-bandgap-prediction_v2.0.0.zip`、`perovskite-v2.0.0.patch` | v2 历史快照，保留可追溯 |
| 各 xlsx（数据集/候选清单/冲突判定/计算设置） | 数据与核验材料，未改动 |

## C. 建议新增（v3 全新产物）

| 本地文件/目录 | 说明 |
|---|---|
| `configs/`（3 个 json） | 超参数外置 + 验收线配置 |
| `src/`（6 个子包，约 20 个 py） | v3 研究内核全部模块 |
| `scripts/`（7 个 py） | train/audit/interpret/active/serve/layered/figures |
| `docs/`（acceptance/methods/references/decisions） | v3 方法/文献/决策/验收文档 |
| `data/raw/perovs_data_final.xlsx` | 只读原始数据副本 |
| `experiments/results/v3_*.json`（8 个） | v3 实验记录（完整字段 + 验收判定） |
| `experiments/figures/4 张 png` | v3 诊断图（覆盖同名旧图） |
| `experiments/active_learning_queue.csv` | 主动学习 DFT 队列（覆盖同名旧文件） |
| `审阅报告_v2.1.md` / `PR_body.md` | 前两轮报告（如需要归档） |

## 待确认

1. 是否按 A 替换 + C 新增上传？B 全部保留。
2. 上传方式：逐文件上传（同名覆盖）还是新增 `v3/` 子目录集中放置？
3. `审阅报告_v2.1.md`、`PR_body.md` 是否一并上传（可选）。
