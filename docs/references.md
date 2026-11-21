# 参考文献（v3）

> 来源声明：以下 7 条**全部**摘自 `优化方案_v2.0.md` 附录 B「参考文献（均已核验标识符）」，
> 逐条保留其标题、作者、年份、期刊、卷期、DOI/PMID 与括注。本版**未新增任何文献**，
> 未检索、未核验的条目一律不列入（宪法 4.1/4.2）。
> 引用格式：GB/T 7714（按优化方案原文抄录）。

[1] Liu Y, Yan W, Zhu H, et al. Study on bandgap predictions of ABX3-type perovskites by machine learning. Organic Electronics, 2022, 101: 106426. DOI:10.1016/j.orgel.2021.106426（227 组实验带隙，RMSE 0.55，SHAP）

[2] Feng S, Wang J. Prediction of Organic-Inorganic Hybrid Perovskite Band Gap by Multiple Machine Learning Algorithms. Molecules, 2024, 29(2): 499. PMID: 38276577（XGBoost MAE 0.0901，R² 0.9913）

[3] Wang H, Ouyang R, Chen W, Pasquarello A. High-Quality Data Enabling Universality of Band Gap Descriptor and Discovery of Photovoltaic Perovskites. J Am Chem Soc, 2024, 146(26): 17636-17645. PMID: 38698551

[4] Xiao L, Liu H, Liu X, et al. Discovering key factors determining perovskite bandgap under data scarcity inspired by knowledge distillation. J Colloid Interface Sci, 2025, 695: 137827. PMID: 40349386（SHAP：B 位电负性首要因素）

[5] Yang C, Chong X, Hu M, et al. Accelerating the Discovery of Hybrid Perovskites with Targeted Band Gaps via Interpretable Machine Learning. ACS Appl Mater Interfaces, 2023, 15(34): 40419-40427. PMID: 37594363

[6] Xie T, Grossman J C. Crystal Graph Convolutional Neural Networks for an Accurate and Interpretable Prediction of Material Properties. Phys Rev Lett, 2018, 120: 145301. DOI:10.1103/PhysRevLett.120.145301

[7] Qian J, Liu Y, Song J, et al. Spectroscopic Limited Practical Efficiency (SLPE) model for organometal halide perovskites solar cells evaluation. Organic Electronics, 2018, 59: 389-398. DOI:10.1016/j.orgel.2018.05.056

## 文献与 RQ 的对应（按优化方案）

- SHAP / 可解释性（本版 `src/interpretation`）：[1][4][5]
- 数据质量与描述符普遍性（本版 `src/data/cleaner`、`src/data/electronic`）：[3]
- 带隙预测模型与口径（本版 `src/models`）：[2][6]
- SLME / 效率导向（后续阶段，本版未纳入）：[7]

> 注意：文献[2] 的 MAE 0.0901 对应 R² 0.9913，是「低 MAE 配高 R²」，
> 与导师验收线「MAE 0.10–0.14 配 R² 0.90–0.94」不同——这是 `docs/acceptance.md` 判定
> 导师区间不自洽的文献佐证之一（provenance: 指标对账_v3.0 §1.2）。
