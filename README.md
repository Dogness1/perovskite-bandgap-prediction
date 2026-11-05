# 钙钛矿研究平台 - Perovskite Band Gap Prediction System

## 项目简介

本项目是一个基于机器学习的钙钛矿带隙预测系统，通过分析钙钛矿材料的化学成分和结构特征，预测其带隙值，为钙钛矿太阳能电池材料研究提供数据支持和决策参考。

## 技术栈

### 前端技术栈
- **框架**: Vue 3.2.47
- **路由**: Vue Router 4.1.6
- **构建工具**: Vue CLI 5.0.8
- **HTTP客户端**: Fetch API
- **样式**: CSS3 + CSS Grid + Flexbox
- **开发服务器**: Vue CLI Dev Server (端口: 8080)

### 后端技术栈
- **框架**: Flask 3.0.3
- **跨域支持**: Flask-CORS 5.0.0
- **数据处理**: Pandas 2.0.3
- **数值计算**: NumPy 1.24.4
- **机器学习**: Scikit-learn 1.3.2（默认 RandomForest 双模型）
- **梯度提升**: XGBoost 1.5.0（可选配置 C2，未设为默认）
- **Excel处理**: openpyxl 3.0.0
- **模型持久化**: joblib 1.1.0

### 开发环境
- **操作系统**: Windows
- **Python版本**: Python 3.8+
- **Node.js版本**: Node.js 14+
- **包管理器**: npm

## 项目功能

### 1. 数据可视化
- **统计卡片展示**: 显示样本总数、平均带隙、A位元素数量、B位元素数量
- **卤素分布图**: 饼图展示Cl、Br、I三种卤素的分布比例
- **带隙分布直方图**: 展示带隙值在不同区间的分布情况
- **卤素-带隙关系**: 展示不同卤素对应的平均带隙和范围
- **样本示例**: 展示数据集中的典型钙钛矿分子式

### 2. 带隙预测
- **输入参数**: A位元素、B位元素、Cl/Br/I比例；可选 `pbe_bandgap`（已有 PBE 计算结果时传入）
- **预测结果**: HSErel_SOC 带隙（PBE 基线 + Δ 修正），同时返回 PBE 分项与 Δ 修正量
- **模型支持**: 两个 RandomForest 回归器（PBE 基线模型 488 样本、Δ 模型 281 个配对样本）
- **两种口径**: 传入 `pbe_bandgap` 时用真值作基线（场景 A，误差只来自 Δ 模型）；不传时 PBE 由模型估算（场景 B，Web API 默认）

### 3. 结构生成
- **目标导向**: 根据目标带隙值生成新的钙钛矿结构
- **智能推荐**: 提供多种满足条件的卤素混合方案
- **参数控制**: 可设置样本数量和带隙容差

### 4. 数据分析
- **结构对比**: 将生成结构与数据集进行对比分析
- **卤素影响**: 分析不同卤素对带隙的影响
- **特征重要性**: 展示各特征对带隙预测的重要性排序

## 项目结构

```
perovskite-bandgap-prediction/
├── frontend/                 # 前端项目
│   ├── src/
│   │   ├── api/           # API接口封装
│   │   ├── pages/         # 页面组件
│   │   ├── router/        # 路由配置
│   │   ├── App.vue        # 根组件
│   │   └── main.js       # 入口文件
│   ├── index.html         # HTML模板
│   ├── package.json       # 依赖配置
│   └── vue.config.js     # Vue配置
├── backend/              # 后端项目
│   ├── analysis/         # 分析模块
│   ├── data/            # 数据处理模块
│   ├── models/          # 模型模块
│   ├── app.py          # Flask主应用（Δ-learning 双模型）
│   ├── train.py        # 离线训练与三套验证（新增）
│   └── requirements.txt # Python依赖
├── d3dd00015j2/       # 数据集
│   └── perovs_data_final.xlsx
├── experiments/
│   └── results/        # train.py 输出的指标 JSON
└── README.md           # 项目说明文档
```

## 部署过程

### 前端部署

#### 1. 环境准备
```bash
# 安装Node.js (建议版本14+)
# 下载地址: https://nodejs.org/

# 检查Node.js版本
node --version
```

#### 2. 安装依赖
```bash
cd frontend
npm install
```

#### 3. 开发环境运行
```bash
npm run dev
```
前端服务将运行在 http://localhost:8080/

#### 4. 生产环境构建
```bash
npm run build
```
构建产物将生成在 `dist/` 目录

### 后端部署

#### 1. 环境准备
```bash
# 安装Python (建议版本3.8+)
# 下载地址: https://www.python.org/

# 检查Python版本
python --version
```

#### 2. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

#### 3. 启动服务
```bash
python app.py
```
后端服务将运行在 http://localhost:5000/

### 完整部署流程

#### 开发环境
```bash
# 终端1: 启动后端服务
cd backend
pip install -r requirements.txt
python app.py

# 终端2: 启动前端服务
cd frontend
npm install
npm run dev
```

访问地址: http://localhost:8080/

#### 生产环境
```bash
# 1. 构建前端
cd frontend
npm run build

# 2. 部署前端
# 将dist/目录内容部署到Web服务器

# 3. 启动后端
cd backend
pip install -r requirements.txt
python app.py
```

## API接口文档

### 健康检查
- **接口**: `GET /api/health`
- **描述**: 检查后端服务状态
- **返回**: `{ status: 'healthy', initialized: boolean }`

### 数据统计
- **接口**: `GET /api/data/stats`
- **描述**: 获取数据集统计信息
- **返回**: 
```json
{
  "total_samples": 488,
  "bandgap_range": { "min": 0.4, "max": 5.4, "mean": 2.81, "std": 1.2 },
  "elements": { "A_sites": [...], "B_sites": [...] },
  "sample_formulas": [...]
}
```

### 数据分布
- **接口**: `GET /api/data/distribution`
- **描述**: 获取数据分布信息
- **返回**:
```json
{
  "halogen_distribution": { "Cl": 127, "Br": 163, "I": 198 },
  "bandgap_histogram": { "bins": [...], "counts": [...] },
  "halogen_bandgap_stats": { "Cl": {...}, "Br": {...}, "I": {...} }
}
```

### 带隙预测
- **接口**: `POST /api/predict`
- **描述**: 预测钙钛矿带隙
- **请求体**:
```json
{
  "a_site": "Cs",
  "b_site": "Pb",
  "cl_ratio": 0.5,
  "br_ratio": 1.5,
  "i_ratio": 1.0,
  "pbe_bandgap": 2.10        // 可选；传入则按场景A用真值作基线
}
```
- **返回**:
```json
{
  "formula": "CsPb(Cl_0.5Br_1.5I_1.0)",
  "predicted_bandgap": 2.96,
  "bandgap_basis": "HSErel_SOC (PBE + Δ-learning)",
  "pbe_source": "provided",
  "pbe_bandgap": 2.10,
  "delta_correction": 0.86,
  "input": { ... }
}
```
`predicted_bandgap` 字段名保持不变，前端无需改动；`pbe_source` 取 `provided` 或 `predicted`。

### 验证指标
- **接口**: `GET /api/metrics`
- **描述**: 返回启动时的 5 折随机 / GroupKFold 快速评估，以及 `train.py` 产出的完整 10×5 与端到端结果

### 结构生成
- **接口**: `POST /api/generate`
- **描述**: 生成新的钙钛矿结构
- **请求体**:
```json
{
  "a_site": "Cs",
  "b_site": "Pb",
  "target_bandgap": 1.8,
  "n_samples": 10,
  "bandgap_tolerance": 0.3
}
```
- **返回**:
```json
{
  "target_bandgap": 1.8,
  "a_site": "Cs",
  "b_site": "Pb",
  "generated_structures": [...],
  "total_generated": 10
}
```

## 数据集说明

### 数据来源
- **文件**: `perovs_data_final.xlsx`
- **样本数量**: 488个钙钛矿样本
- **特征**: 化学成分、结构参数、带隙值、SLME效率等

### 数据预处理
- **特征提取**: 从分子式中提取A位、B位元素和卤素比例
- **特征工程**: 添加容忍因子、八面体因子等结构特征
- **数据标准化**: 使用StandardScaler进行特征标准化

### 模型训练与评估口径（v2.0）

**数据**：`perovs_data_final.xlsx` 的 PBE sheet（488 样本）与 HSErel_SOC sheet（282 行），按 `Formula` 一一配对得到 281 个 Δ 标签，Δ = gap_HSE_SOC − gap_PBE。特征共 34 维（A 位 6 + B 位 14 + 卤素比例 3 + 离子半径 3 + 结构描述子 8）。配对时保留 PBE 全量列，否则 8 个结构描述子会被静默丢弃（26 维），实测 MAE 相差 25%。

**模型**：两个 `RandomForestRegressor(n_estimators=200, max_depth=10)`：
- PBE 基线模型：488 个 PBE 样本，输入组分 → PBE 带隙
- Δ 模型：281 个配对样本，输入组分 → Δ

**两种口径必须分开报**，这是 v2.0 最重要的修正：

| 场景 | 输入 | 计算式 | 随机 10×5 CV | GroupKFold(5) |
|---|---|---|---|---|
| A：已有 PBE 结果（Δ-learning 标准用法） | 组分 + PBE 真值 | PBE_true + Δ_pred | R² 0.9377 / MAE 0.2761 eV | R² 0.9227 / MAE 0.3122 eV |
| B：仅组分（Web API 默认） | 组分 | PBE_pred + Δ_pred | R² 0.7481 / MAE 0.5453 eV | R² 0.7308 / MAE 0.5819 eV |

场景 B 明显更差，因为 PBE 模型自身的预测误差会叠加进来。此前 README 声称的「XGBoost / 80-20 划分 / R²>0.85, MAE<0.3 eV」与实际代码（RandomForest）及本轮实测均不一致，已删除。对外引用精度时必须注明口径。

**三套验证**：随机 `RepeatedKFold(5×10)`（插值）、`GroupKFold(5, groups=A_B)`（A/B 外推）、独立外部测试集（尚未建立；`--external` 只是从现有配对样本按组切出的代理集，不可作主结论）。

### 训练与校验命令

```bash
cd backend
python -m py_compile app.py train.py data/preprocessor.py models/predictor.py
python -m pyflakes app.py train.py data/preprocessor.py models/predictor.py
python train.py --check-shapes             # 只校验数据形状，不训练
python train.py --config C1 --dry-run      # 1 折 / 10 棵树，验证链路
python train.py --config C1 --full         # 10x5 重复 CV + GroupKFold(5)
python train.py --config C1 --full --external  # 额外跑代理外部集
```

结果写入 `experiments/results/latest.json`，并自动被 `GET /api/metrics` 读取。

## 常见问题

### Q: 前端无法访问后端API？
A: 检查后端服务是否启动，确保后端运行在 http://localhost:5000/

### Q: 前端页面显示"加载中..."？
A: 后端服务未启动或API调用失败，启动后端服务即可

### Q: 如何更换数据集？
A: 将新的Excel文件放到 `d3dd00015j2/` 目录，并修改 `backend/app.py` 中的数据路径

### Q: 如何重新训练模型？
A: 重启后端服务会自动训练 PBE 与 Δ 两个模型；如需完整的三套验证指标与可归档的结果文件，运行 `python backend/train.py --config C1 --full`。

## 开发规范

### 代码风格
- **前端**: 遵循Vue 3官方风格指南
- **后端**: 遵循PEP 8代码规范
- **注释**: 关键函数和复杂逻辑需要添加注释

### Git提交规范
- **feat**: 新功能
- **fix**: 修复bug
- **docs**: 文档更新
- **style**: 代码格式调整
- **refactor**: 代码重构
- **test**: 测试相关
- **chore**: 构建/工具链相关

## 许可证

MIT License

## 联系方式

如有问题或建议，请联系项目维护者。

---

**项目版本**: v2.0.0（Δ-learning 双模型 + 三套验证）  
**最后更新**: 2026-11-05