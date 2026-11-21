# 方法与架构（v3）

> 事实来源：优化方案_v2.0「五步执行顺序」、指标对账_v3.0、本机实测、本轮用户决策。
> 本版按导师五步路线重写研究内核；文献严格限于 `docs/references.md` 七条已核验条目。

## 1. 目标与口径

目标：由组分（A/B 位 + Cl/Br/I 比例）预测 HSErel_SOC 带隙。
模型学 Δ = gap_HSE − gap_PBE，最终预测 = PBE + Δ_pred。两种口径必须分开报：

- **end_to_end**（主指标）：PBE_pred + Δ_pred，仅组分输入，API 默认。
- **oracle_pbe**：PBE_true + Δ_pred，Δ-learning 上限参考，非部署场景。

验收线见 `docs/acceptance.md`（R² 沿用导师区间，MAE 按 std=1.4746 上修）。
验收判定对 **oracle_pbe** 口径执行（导师历史口径，证据见 acceptance.md §2.5）；
end_to_end 为部署口径单独报告，不拿导师区间判定。

## 2. 导师五步路线 → 本版模块映射

| 步骤 | 导师要求 | 本版实现 | 状态 |
|---|---|---|---|
| 第0步 信噪比清洗 | Δ 配对校验、B 位分层、3σ 回查、τ 异常、收敛占位 | `src/data/loader.py`、`src/data/cleaner.py`、`scripts/audit.py` | 已实现；3σ 候选 0、τ 异常 4（只标不删） |
| 第1步 样本加权+分层 | 10×10 卤素网格加权、分层 | `src/data/dataset.py::grid_weights` | 已实现；C2 实测无增益（负面结果如实保留） |
| 第2步 三套验证+诊断图 | 随机10×5 / GroupKFold / 独立外部集 + 4 类图 | `src/evaluation/` | 已实现；外部集为 group-disjoint 划组，非独立数据源 |
| 第3步 不确定性+主动学习 | 树间标准差、候选采样、DFT 队列 | `src/active/candidate.py`、`scripts/active.py` | 已实现；目标窗口候选 0（如实记录） |
| 第4步 外部测试集收口 | 提前锁定独立集 | `configs/base.json::evaluation.external` | 部分实现；真正独立数据需用户提供 |

## 3. 数据与特征

- 数据 `data/raw/perovs_data_final.xlsx`（只读）：PBE 488 行、HSErel_SOC 282 行，按 Formula 配对得 281 个 Δ 标签。
- 基础 34 维：A 位 one-hot(6) + B 位 one-hot(14) + 卤素比例(3) + 离子半径(3) + 结构描述子(8)。
- 电子描述子（可选，+5 维）：电负性/价电子，见 `src/data/electronic.py`；
  MA/FA 为组成元素近似启发值，非核验数据。
- 结构描述子训练时取真实 DFT 值，推理时缺省用训练集列均值填充（API 可传真值覆盖）。
  SHAP 显示模型重度依赖这些特征——这是已知 train-serve 局限，见 `docs/decisions/DEC-v3-002`。

## 4. 评估器（冻结）

seed=42。三套验证：随机 RepeatedKFold(5×10)、GroupKFold(5, groups=A_B)、
group-disjoint 外部集（默认划 K_Ca 22 样本）。每折 PBE 基线模型在训练集重训，不泄露测试折标签。
实验记录字段完整（实验ID/配置hash/代码commit/数据集/seed/指标/验收判定/结论），
新实验线标注 `new_line` 且不与基线直接对比（宪法 3.1/3.2/3.4）。

## 5. 目录约定（宪法 2.3）

```
configs/   实验配置（超参数外置）
data/raw/  只读原始数据
src/       可复用模块（data/models/evaluation/interpretation/active/api）
scripts/   入口脚本（train/audit/interpret/active/serve）
experiments/ 运行产物（results/figures/queue）
docs/      文稿与记录（方法/文献/决策/验收）
tests/     测试
```

## 6. 可复现命令

```bash
cd repo
python scripts/audit.py                          # 第0步 标签审计
python scripts/train.py --config c1_delta_rf.json --dry-run
python scripts/train.py --config c1_delta_rf.json # 正式三套验证
python scripts/train.py --config c3_electronic_external.json
python scripts/interpret.py                      # SHAP
python scripts/active.py                         # 主动学习队列
python scripts/serve.py                          # API :5000
```
