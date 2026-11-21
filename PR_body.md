## 概述

对仓库做全局代码审阅并按确认方案更正，重训复现冻结基线，新增 4 条独立实验线与导师方案增量工程。所有实验线标注 `new_line=true`、`comparable_to_C1_baseline=false`，不与冻结基线直接对比。

## 核心更正（5 项，不动评估器）
- 生成器 `_predict_bandgap()` 接回真实 Δ 预测器（此前始终走固定启发式，`/api/generate` 绕过模型口径，见 MD-005 still_open#1）
- 结构描述子默认值 0.01 → 训练集列均值（train-serve skew 修复）
- 补 `scipy` 依赖、修 predictor.py docstring、更新 CLAUDE.md
- C1 冻结基线复现：随机 10×5 端到端 R²0.7483/MAE0.5450、oracle R²0.9377/MAE0.2759，与 v2.0 一致

## API 输入改造（处置 SHAP 暴露的 F6 矛盾）
- `/api/predict`、`/api/predict/batch` 新增 8 个结构描述子入参（有 DFT 值时填真值，缺省回退均值）
- 新增 `GET /api/structure-defaults`；返回 `structure_source`
- 前端预测页新增"高级选项：结构描述子"折叠区，dist 已重建

## 新实验线（4 条）
| 实验 | 结果 | 结论 |
|---|---|---|
| L1-SHAP | Top 特征全为结构描述子 | 暴露模型重度依赖推理时均值填充的特征 |
| L2 Pb/Sn 分层 | R²0.6920/MAE0.3740 (n=54) | 待定，覆盖 19.2% |
| L2b 6 位分层 | R²0.9395/MAE0.2562 (n=281) | 待定，小层回代偏乐观 |
| L3 电子描述子+外部集 | 外部 R²0.9563/MAE0.2367 (n=22) | 待定，参数为近似值 |

## 导师方案工程
- 第0步 标签校验：6 位分层 3σ 候选 0、τ 异常 4（只标不删）、is_converged 占位
- 第2步 诊断图 4 张（预测散点/残差/三元 MAE 热图/不确定性-误差）
- 第3步 主动学习队列 30 条；目标带隙窗口内候选 0（如实记录）

## 验证
`py_compile` 全通过；`train.py --check-shapes` 三配置通过；Flask 全路由冒烟 200；API 结构参数生效（预测值由 2.8357→2.8575 eV）；前端 build 成功。

详见 `审阅报告_v2.1.md` 与 `CHANGELOG.md`。所有负面结果如实保留，未删除失败实验。
