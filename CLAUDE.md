# CLAUDE.md

本文件为在本仓库中工作的 AI 助手提供项目上下文与操作约定。

## 项目状态

钙钛矿带隙预测系统 **v3 研究内核**（按导师五步路线全量重写，config 驱动）。
目标：由组分（A/B 位 + Cl/Br/I 比例）预测 HSErel_SOC 带隙；
`predicted_bandgap` 语义为 HSErel_SOC（= PBE 基线 + Δ 修正），比 PBE 高约 0.8 eV。
历史 v2.x 代码保留在 `backend/` 与 `frontend/` 供对照，v3 源码在 `src/` + `scripts/`。

## 架构与关键模式

- `src/data/`：loader（Formula 配对校验）、preprocessor（34 维特征 + 结构默认值）、
  electronic（电负性/价电子，MA/FA 为近似）、cleaner（Δ 按 B 位 3σ + τ）、dataset（配对切分 + 缩放）。
- `src/models/`：delta（PBE 基线 + Δ 双模型）、layered（B 位分层）。
- `src/evaluation/`：splitter（三套验证，PBE 基线折内重训不泄露）、
  metrics（R²/MAE/RMSE + 上修验收判定）、diagnostics（4 类图）。
- `src/interpretation/`：SHAP TreeExplainer；`src/active/`：主动学习队列。
- `src/api/`：PredictorService（推理封装）+ Flask 薄层；支持 8 个结构描述子真值入参。
- `scripts/`：train / audit / interpret / active / serve 五个入口。
- `configs/`：超参数全部外置，extends 深合并。数据 `data/raw/` 只读。

## 评估口径（冻结，勿随意改动）

- end_to_end = PBE_pred + Δ_pred（主指标，API 默认）；oracle_pbe = PBE_true + Δ_pred（上限参考）。
- 三套验证：随机 RepeatedKFold(5×10)、GroupKFold(5, groups=A_B)、group-disjoint 外部集。
- seed=42。**验收线**：R² 沿用导师区间（随机 0.90–0.94），MAE 按 std=1.4746 上修
  （随机 0.29–0.37），见 `docs/acceptance.md`（DEC-v3-001）。导师原 MAE 0.10–0.14 与该 std 数学不自洽。
- **验收判定对 oracle_pbe 口径**（导师历史口径）；end_to_end 为部署口径，不拿导师区间判定。

## 构建、测试与校验命令

```bash
python scripts/audit.py
python scripts/train.py --config c1_delta_rf.json --dry-run
python scripts/train.py --config c1_delta_rf.json
python scripts/train.py --config c3_electronic_external.json
python scripts/interpret.py
python scripts/active.py
python scripts/serve.py    # :5000（前端 dist 在 frontend/dist/）
```

## 已知局限

- 结构描述子在推理时只能用训练均值填充（API 可传真值覆盖），SHAP 显示模型重度依赖它们（DEC-v3-002）。
- 严格三元（Cl/Br/I 均>0）样本 0；B 位 6 种（Ca/Ba/Sr/Sn/Ge/Pb），Pb/Sn 分层仅覆盖 19.2%。
- 外部集为 group-disjoint 划组，非独立数据源；真正独立集需用户提供。
- MA/FA 电负性/价电子为组成元素近似启发值，非核验数据（已注明）。
- 文献仅 `docs/references.md` 七条已核验条目，未新增（宪法 4.1）。
