# CLAUDE.md

本文件为在本仓库中工作的 AI 助手提供项目上下文与操作约定。

## 项目状态

钙钛矿带隙预测系统 v2.1（Δ-learning 双模型 + 三套验证）。
目标：由组分（A/B 位 + Cl/Br/I 比例）预测 HSErel_SOC 带隙；
`predicted_bandgap` 字段语义为 HSErel_SOC（= PBE 基线 + Δ 修正），整体比 PBE 高约 0.8 eV。

## 架构与关键模式

- `backend/app.py`：Flask API。启动时训练两个 RandomForest（PBE 基线 488 样本、Δ 模型 281 配对样本），
  用 `DeltaCorrectedPredictor` 组合。推理时结构描述子用训练集列均值填充
  （`preprocessor.fit_structure_defaults`），不硬编码 0.01。
- `backend/data/preprocessor.py`：化学式解析（含混合 A 位的 B 位回退）、34 维特征构造、结构默认值学习。
- `backend/data/feature_engineer.py`：StandardScaler（树模型下全局 fit 可接受；换线性/NN 必须折内 fit）。
- `backend/models/predictor.py`：`BandGapPredictor`，支持 RF/XGB/GB，含 sample_weight 透传与 CV。
- `backend/models/generator.py`：反向结构生成；`_predict_bandgap` 已接回真实 Δ 预测器
  （依赖不全时回退启发式）。
- `backend/analysis/comparator.py`：生成结构与数据集对比。
- `backend/train.py`：离线训练与三套验证，配置 C0/C1/C2，结果写 `experiments/results/`。
- 数据：`d3dd00015j2/perovs_data_final.xlsx`，PBE sheet 488 行、HSErel_SOC sheet 282 行，
  按 Formula 一一配对得 281 个 Δ 标签。

## 评估口径（冻结，勿随意改动）

- 场景 A（oracle_pbe）：PBE_true + Δ_pred —— 已有 PBE 计算结果时使用。
- 场景 B（end_to_end）：PBE_pred + Δ_pred —— 仅组分输入，Web API 默认，误差更高。
- 三套验证：随机 RepeatedKFold(5×10)、GroupKFold(5, groups=A_B)、
  代理外部集（`--external`，非独立数据源，禁止写入论文主结论）。
- seed=42。旧 C1 基线见 `experiments/results/train_C1.json`。

## 构建、测试与校验命令

```bash
cd backend
python -m py_compile app.py train.py data/preprocessor.py data/feature_engineer.py \
    models/predictor.py models/generator.py analysis/comparator.py
python train.py --check-shapes
python train.py --config C1 --dry-run
python train.py --config C1 --full
# 启动服务：python app.py（:5000）；前端：cd frontend && npm run dev（:8080）
```

## 依赖

`backend/requirements.txt`（含 scipy）。前端 Node 14+，后端 Python 3.8+。

## 已知局限

- 训练用真实 DFT 结构描述子，推理（API/生成）只能用训练集均值填充；结构描述子本质需结构输入。
- 严格三元（Cl/Br/I 均>0）样本为 0，三元调控属训练分布外。
- B 位共 6 种（Ca/Ba/Sr/Sn/Ge/Pb），Pb/Sn 分层仅覆盖 54/281 配对样本。
- `frontend/dist/` 为旧构建产物，源码口径标注需 `npm run build` 才生效。
