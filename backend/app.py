"""
Flask API 主应用
三维钙钛矿卤素调控与带隙预测系统后端API

v2.0 口径变更：主输出改为 HSErel_SOC 带隙，采用 Δ-learning
（PBE 基线模型 + Δ 修正模型），并保留 PBE 分项与三套验证指标。
"""

import os
import sys
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.preprocessor import PerovskitePreprocessor
from data.feature_engineer import FeatureEngineer
from models.predictor import BandGapPredictor
from models.generator import HalogenStructureGenerator
from analysis.comparator import StructureComparator

app = Flask(__name__)
CORS(app)


# API 短参数名 -> 结构描述子列名（与 preprocessor.STRUCTURE_COLS 对齐）
# 用途：让调用方传入真实 DFT 结构描述子，缓解 F6（模型重度依赖这些特征但
# 旧 API 一律填 0.01/均值）的 train-serve 矛盾。短名便于前端与批量接口使用。
STRUCTURE_PARAM_MAP = {
    'cubicity_b': 'Deviation of Cubicity b axis',
    'cubicity_c': 'Deviation of Cubicity c axis',
    'cubicity_alpha': 'Deviation of Cubicity at alpha',
    'cubicity_beta': 'Deviation of Cubicity at beta',
    'cubicity_gamma': 'Deviation of Cubicity at gamma',
    'octahedral_factor': 'Octaehdral Factor',
    'tolerance_factor': 'Tolerance Factor',
    'bartel_tolerance': "Bartel's Tolerance Factor",
}


def structure_values_from_request(data):
    """从请求体提取 8 个结构描述子；未提供或非法者用训练均值填充。

    in : data(dict) 请求 JSON（可为单条或 batch 中的单条结构）
    out: dict{结构列名: float}，键与 create_feature_matrix 期望一致
    """
    defaults = model_state.get('structure_defaults', {})
    out = {}
    for param, col in STRUCTURE_PARAM_MAP.items():
        val = data.get(param, None)
        if val is not None:
            try:
                out[col] = float(val)
                continue
            except (TypeError, ValueError):
                pass
        out[col] = defaults.get(col, 0.0)
    return out


class DeltaCorrectedPredictor:
    """PBE 基线模型 + Δ 修正模型 → HSErel_SOC 带隙。

    保持 BandGapPredictor 的 predict / predict_with_uncertainty /
    get_feature_importance 接口，使生成器与所有 API 路由无需改动即可用新口径。

    推理：gap_HSE = pbe_model.predict(X) + delta_model.predict(X)
    其中 Δ = gap_HSErel_SOC − gap_PBE，在 281 个配对样本上训练。
    """

    def __init__(self, pbe_model, delta_model):
        self.pbe_model = pbe_model
        self.delta_model = delta_model

    def predict(self, X: np.ndarray) -> np.ndarray:
        """in: X (n,d) -> out: (n,) HSErel_SOC 带隙"""
        return self.pbe_model.predict(X) + self.delta_model.predict(X)

    def predict_components(self, X: np.ndarray):
        """in: X (n,d) -> out: (pbe (n,), delta (n,), hse (n,))"""
        pbe = self.pbe_model.predict(X)
        delta = self.delta_model.predict(X)
        return pbe, delta, pbe + delta

    def predict_with_uncertainty(self, X: np.ndarray, n_estimators: int = 100):
        mean, std = self.pbe_model.predict_with_uncertainty(X, n_estimators)
        return mean + self.delta_model.predict(X), std

    def get_feature_importance(self):
        return self.pbe_model.get_feature_importance()


# 全局变量存储模型和数据
model_state = {
    'predictor': None,          # DeltaCorrectedPredictor（组合口径，供 API/生成器）
    'pbe_predictor': None,      # 488 样本上训练的 PBE 基线模型
    'delta_predictor': None,    # 281 配对样本上训练的 Δ 模型
    'generator': None,
    'preprocessor': None,
    'data': None,
    'paired_data': None,
    'feature_engineer': None,
    'metrics': None,
    'is_initialized': False
}


def initialize_models():
    """初始化模型和数据（Δ-learning 双模型口径，v2.0）。"""
    if model_state['is_initialized']:
        return

    print("Initializing models (PBE + Δ -> HSErel_SOC)...")

    data_path = os.path.join(os.path.dirname(__file__), '..', 'd3dd00015j2', 'perovs_data_final.xlsx')
    if not os.path.exists(data_path):
        print(f"Warning: Data file not found at {data_path}")
        return

    # --- 1. 数据加载：PBE 全量 488 + HSErel_SOC 配对 281 -----------------
    pbe_df = pd.read_excel(data_path, sheet_name='PBE')             # (488, 12)
    hse_df = pd.read_excel(data_path, sheet_name='HSErel_SOC')      # (282, 4)
    model_state['data'] = pbe_df

    # 关键：merge 左表保留 PBE 全部列。只取 [['Formula','Band Gap (eV)']]
    # 会静默丢掉 8 个结构描述子，使特征从 34 维塌成 26 维（v3.0 实测
    # 该差异带来 25.2% 的 MAE 变化）。validate 保证标签一一配对。
    paired = pbe_df.merge(
        hse_df[['Formula', 'Band Gap (eV)']], on='Formula',
        suffixes=('_PBE', '_HSE'), validate='one_to_one',
    )                                                               # (281, 13)
    model_state['paired_data'] = paired

    prep = PerovskitePreprocessor()
    model_state['preprocessor'] = prep
    # 学习 8 个结构描述子的训练均值，作为 API/生成器的中性默认值，
    # 替代 v2.0 硬编码的 0.01（与训练分布严重不符，见 preprocessor.fit_structure_defaults）
    structure_defaults = prep.fit_structure_defaults(pbe_df)
    model_state['structure_defaults'] = structure_defaults

    # --- 2. 特征矩阵：两个数据集共用同一套 34 维描述子 -------------------
    pbe_parsed = prep.extract_features(pbe_df)
    paired_parsed = prep.extract_features(
        paired.rename(columns={'Band Gap (eV)_PBE': 'Band Gap (eV)'})
    )
    X_pbe, y_pbe, feature_names = prep.create_feature_matrix(pbe_parsed, include_target=True)
    X_pair, _, _ = prep.create_feature_matrix(paired_parsed, include_target=False)
    X_pbe = np.nan_to_num(np.asarray(X_pbe, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    X_pair = np.nan_to_num(np.asarray(X_pair, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    y_pbe = np.nan_to_num(np.asarray(y_pbe, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)

    fe = FeatureEngineer()
    model_state['feature_engineer'] = fe
    # 树模型对单调线性缩放不敏感，scaler 在 488 全量上 fit 后两模型共用；
    # 若换线性/神经网络模型，必须改为折内 fit。
    X_pbe_s = fe.fit_transform(X_pbe, feature_names)                # (488, 34)
    X_pair_s = fe.transform(X_pair)                                  # (281, 34)

    # --- 3. Δ 目标与 (A,B) 分组标签 --------------------------------------
    y_hse = paired['Band Gap (eV)_HSE'].to_numpy(float)             # (281,)
    y_pbe_pair = paired['Band Gap (eV)_PBE'].to_numpy(float)        # (281,)
    delta = y_hse - y_pbe_pair                                       # (281,)
    # dtype=object 是必须的：numpy str dtype 会被 sklearn check_array
    # 尝试转 float，从而在 GroupKFold 中报 "Input contains NaN"。
    groups = np.array(
        [f'{a}_{b}' for a, b in zip(paired_parsed['A_site'], paired_parsed['B_site'])],
        dtype=object,
    )                                                               # (281,)

    # --- 4. 训练双模型 ----------------------------------------------------
    pbe_model = BandGapPredictor(model_type='random_forest')
    pbe_model.train(X_pbe_s, y_pbe, feature_names=feature_names)     # 目标：PBE 带隙
    delta_model = BandGapPredictor(model_type='random_forest')
    delta_model.train(X_pair_s, delta, feature_names=feature_names)   # 目标：Δ

    model_state['pbe_predictor'] = pbe_model
    model_state['delta_predictor'] = delta_model
    model_state['predictor'] = DeltaCorrectedPredictor(pbe_model, delta_model)

    # --- 5. 快速 5 折 + GroupKFold 评估（完整 10x5 见 backend/train.py）--
    from sklearn.model_selection import KFold, GroupKFold
    from sklearn.metrics import r2_score, mean_absolute_error

    def cv_metrics(splitter):
        ys, ps = [], []
        for tr, te in splitter:
            m = BandGapPredictor(model_type='random_forest')
            m.train(X_pair_s[tr], delta[tr], feature_names=feature_names)
            ys.append(y_hse[te])
            ps.append(y_pbe_pair[te] + m.predict(X_pair_s[te]))
        y, p = np.concatenate(ys), np.concatenate(ps)
        return {
            'r2': float(r2_score(y, p)),
            'mae': float(mean_absolute_error(y, p)),
            'rmse': float(np.sqrt(np.mean((y - p) ** 2))),
            'n': int(len(y)),
        }

    model_state['metrics'] = {
        'basis': 'HSErel_SOC = PBE_true(oracle) + Δ_pred（场景A：已有 PBE 结果）；'
                 '仅组分输入的端到端口径见 backend/train.py',
        'pbe_samples': int(len(pbe_df)),
        'paired_samples': int(len(paired)),
        'n_features': int(len(feature_names)),
        'model': 'RandomForest(n_estimators=200, max_depth=10)',
        'delta_stats': {
            'mean': float(delta.mean()), 'std': float(delta.std()),
            'min': float(delta.min()), 'max': float(delta.max()),
        },
        'random_5fold': cv_metrics(KFold(5, shuffle=True, random_state=42).split(X_pair_s)),
        'group_5fold': cv_metrics(GroupKFold(5).split(X_pair_s, delta, groups=groups)),
    }
    r5 = model_state['metrics']['random_5fold']
    print(f"Model trained: PBE={len(pbe_df)}, paired={len(paired)}, d={len(feature_names)}")
    print(f"  random 5-fold (oracle PBE): R2={r5['r2']:.4f}, MAE={r5['mae']:.4f} eV")
    print("  仅组分输入的端到端指标请运行: python backend/train.py --full")

    # --- 6. 生成器 --------------------------------------------------------
    model_state['generator'] = HalogenStructureGenerator(
        predictor=model_state['predictor'],
        preprocessor=prep,
        feature_engineer=fe,
        structure_defaults=structure_defaults,
    )

    model_state['is_initialized'] = True
    print("Models initialized successfully!")


# ==================== API 路由 ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'initialized': model_state['is_initialized']
    })


@app.route('/api/data/stats', methods=['GET'])
def get_data_stats():
    """获取数据集统计信息"""
    if not model_state['is_initialized']:
        initialize_models()

    if model_state['data'] is None:
        return jsonify({'error': 'Data not loaded'}), 500

    df = model_state['data']
    elements = model_state['preprocessor'].get_available_elements(df)

    # 基础统计
    stats = {
        'total_samples': len(df),
        'bandgap_basis': 'PBE（原始数据集口径；预测接口输出为 HSErel_SOC）',
        'hse_paired_samples': (
            len(model_state['paired_data']) if model_state['paired_data'] is not None else 0
        ),
        'model_basis': 'HSErel_SOC (PBE + Δ-learning)',
        'bandgap_range': {
            'min': float(df['Band Gap (eV)'].min()),
            'max': float(df['Band Gap (eV)'].max()),
            'mean': float(df['Band Gap (eV)'].mean()),
            'std': float(df['Band Gap (eV)'].std())
        },
        'slme_range': {
            'min': float(df['SLME @ 5um'].min()),
            'max': float(df['SLME @ 5um'].max()),
            'mean': float(df['SLME @ 5um'].mean())
        },
        'elements': elements,
        'sample_formulas': df['Formula'].head(20).tolist()
    }

    return jsonify(stats)


@app.route('/api/data/distribution', methods=['GET'])
def get_data_distribution():
    """获取数据分布信息（用于可视化）"""
    if not model_state['is_initialized']:
        initialize_models()

    df = model_state['data']
    if df is None:
        return jsonify({'error': 'Data not loaded'}), 500

    # 解析卤素信息
    def get_main_halogen(formula):
        for h in ['Cl', 'Br', 'I']:
            if h in str(formula):
                return h
        return 'Unknown'

    df_copy = df.copy()
    df_copy['main_halogen'] = df_copy['Formula'].apply(get_main_halogen)

    # 卤素分布
    halogen_dist = df_copy['main_halogen'].value_counts().to_dict()

    # 带隙分布
    bandgap_bins = np.linspace(0, 6, 13)
    bandgap_hist, _ = np.histogram(df['Band Gap (eV)'], bins=bandgap_bins)

    # 按卤素分组的带隙统计
    halogen_bandgap = {}
    for h in ['Cl', 'Br', 'I']:
        mask = df_copy['main_halogen'] == h
        if mask.any():
            subset = df[mask]
            halogen_bandgap[h] = {
                'mean': float(subset['Band Gap (eV)'].mean()),
                'std': float(subset['Band Gap (eV)'].std()),
                'min': float(subset['Band Gap (eV)'].min()),
                'max': float(subset['Band Gap (eV)'].max()),
                'count': int(len(subset))
            }

    distribution = {
        'halogen_distribution': halogen_dist,
        'bandgap_histogram': {
            'bins': bandgap_bins.tolist(),
            'counts': bandgap_hist.tolist()
        },
        'halogen_bandgap_stats': halogen_bandgap
    }

    return jsonify(distribution)


@app.route('/api/predict', methods=['POST'])
def predict_bandgap():
    """
    预测带隙

    请求体:
    {
        "a_site": "Cs",
        "b_site": "Pb",
        "cl_ratio": 0.5,
        "br_ratio": 1.5,
        "i_ratio": 1.0
    }
    """
    if not model_state['is_initialized']:
        initialize_models()

    data = request.get_json()

    try:
        a_site = data.get('a_site', 'Cs')
        b_site = data.get('b_site', 'Pb')
        cl_ratio = float(data.get('cl_ratio', 0))
        br_ratio = float(data.get('br_ratio', 0))
        i_ratio = float(data.get('i_ratio', 0))
        # 可选：调用方若已有 PBE 计算结果，直接作为基线（Δ-learning 标准场景，
        # 精度显著高于由 PBE 模型估算的"纯组分"场景），见 README 口径说明。
        pbe_override = data.get('pbe_bandgap', None)
        # 是否显式提供了任一结构描述子（用于前端提示预测可信度）
        structure_source = ('provided' if any(data.get(p) is not None
                                              for p in STRUCTURE_PARAM_MAP) else 'default_mean')

        # 构建特征
        # 创建临时DataFrame用于特征提取
        temp_df = pd.DataFrame([{
            'Formula': f"{a_site}{b_site}Cl_{cl_ratio}Br_{br_ratio}I_{i_ratio}",
            'A_site': a_site,
            'B_site': b_site,
            'Cl_ratio': cl_ratio,
            'Br_ratio': br_ratio,
            'I_ratio': i_ratio,
            'Band Gap (eV)': 0  # 占位符
        }])

        # 结构描述子：优先用请求体传入的真实值，缺省回退训练集列均值
        for col, val in structure_values_from_request(data).items():
            temp_df[col] = val

        X, _, _ = model_state['preprocessor'].create_feature_matrix(temp_df, include_target=False)
        X_scaled = model_state['feature_engineer'].transform(X)

        # 预测：主口径 HSErel_SOC = PBE 基线 + Δ 修正
        predictor = model_state['predictor']
        if hasattr(predictor, 'predict_components'):
            pbe_pred, delta_pred, _ = predictor.predict_components(X_scaled)
        else:  # 兼容未启用 Δ 的旧模型
            pbe_pred = predictor.predict(X_scaled)
            delta_pred = np.zeros_like(pbe_pred)

        if pbe_override is not None:
            pbe_base = np.array([float(pbe_override)])
            pbe_source = 'provided'
        else:
            pbe_base = pbe_pred
            pbe_source = 'predicted'
        hse_pred = pbe_base + delta_pred

        result = {
            'formula': f"{a_site}{b_site}(Cl_{cl_ratio}Br_{br_ratio}I_{i_ratio})",
            'predicted_bandgap': float(hse_pred[0]),
            'bandgap_basis': 'HSErel_SOC (PBE + Δ-learning)',
            'pbe_source': pbe_source,
            'structure_source': structure_source,
            'pbe_bandgap': float(pbe_base[0]),
            'delta_correction': float(delta_pred[0]),
            'input': {
                'a_site': a_site,
                'b_site': b_site,
                'cl_ratio': cl_ratio,
                'br_ratio': br_ratio,
                'i_ratio': i_ratio
            }
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/generate', methods=['POST'])
def generate_structures():
    """
    生成新的卤素混合结构

    请求体:
    {
        "a_site": "Cs",
        "b_site": "Pb",
        "target_bandgap": 1.8,
        "n_samples": 10,
        "bandgap_tolerance": 0.3
    }
    """
    if not model_state['is_initialized']:
        initialize_models()

    data = request.get_json()

    try:
        a_site = data.get('a_site', 'Cs')
        b_site = data.get('b_site', 'Pb')
        target_bandgap = float(data.get('target_bandgap', 2.0))
        n_samples = int(data.get('n_samples', 10))
        bandgap_tolerance = float(data.get('bandgap_tolerance', 0.5))

        # 生成结构
        generated = model_state['generator'].generate(
            a_site=a_site,
            b_site=b_site,
            target_bandgap=target_bandgap,
            n_samples=n_samples,
            bandgap_tolerance=bandgap_tolerance
        )

        result = {
            'target_bandgap': target_bandgap,
            'a_site': a_site,
            'b_site': b_site,
            'generated_structures': generated,
            'total_generated': len(generated)
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/analyze', methods=['POST'])
def analyze_structure():
    """
    分析生成结构与数据集对比

    请求体:
    {
        "generated_structure": {...}
    }
    """
    if not model_state['is_initialized']:
        initialize_models()

    data = request.get_json()
    generated_structure = data.get('generated_structure', {})

    try:
        comparator = StructureComparator(dataset_df=model_state['data'])
        comparison = comparator.compare_with_dataset(generated_structure)

        return jsonify(comparison)

    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/halogen-effect', methods=['GET'])
def get_halogen_effect():
    """获取卤素对带隙的影响分析"""
    if not model_state['is_initialized']:
        initialize_models()

    try:
        effect_analysis = model_state['generator'].analyze_halogen_effect(model_state['data'])
        return jsonify(effect_analysis)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/feature-importance', methods=['GET'])
def get_feature_importance():
    """获取特征重要性"""
    if not model_state['is_initialized']:
        initialize_models()

    try:
        importance_df = model_state['predictor'].get_feature_importance()
        return jsonify({
            'feature_importance': importance_df.to_dict('records')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """返回验证指标：启动时的快速 5 折 + train.py 的完整 10x5/GroupKFold 结果"""
    if not model_state['is_initialized']:
        initialize_models()

    result = dict(model_state['metrics'] or {})
    metrics_path = os.path.join(
        os.path.dirname(__file__), '..', 'experiments', 'results', 'latest.json'
    )
    if os.path.exists(metrics_path):
        with open(metrics_path, encoding='utf-8') as f:
            result['offline_full'] = json.load(f)
    else:
        result['offline_full'] = None
        result['hint'] = '运行 python backend/train.py --full 生成完整三套验证结果'
    return jsonify(result)


@app.route('/api/elements', methods=['GET'])
def get_available_elements():
    """获取可用的A位、B位元素列表"""
    if not model_state['is_initialized']:
        initialize_models()

    return jsonify({
        'A_sites': model_state['preprocessor'].A_SITES,
        'B_sites': model_state['preprocessor'].B_SITES,
        'halogens': model_state['preprocessor'].HALOGENS
    })


@app.route('/api/structure-defaults', methods=['GET'])
def get_structure_defaults():
    """返回 8 个结构描述子的 API 参数名、中文标签与训练均值。

    前端"高级选项"用此接口预填默认值；用户若有 DFT 计算结果可覆盖。
    """
    if not model_state['is_initialized']:
        initialize_models()
    labels = {
        'cubicity_b': '立方度偏差 b 轴', 'cubicity_c': '立方度偏差 c 轴',
        'cubicity_alpha': '立方度偏差 α', 'cubicity_beta': '立方度偏差 β',
        'cubicity_gamma': '立方度偏差 γ', 'octahedral_factor': '八面体因子',
        'tolerance_factor': '容忍因子', 'bartel_tolerance': "Bartel 容忍因子",
    }
    defaults = model_state.get('structure_defaults', {})
    fields = [
        dict(param=param, label=labels[param], column=col,
             default=float(defaults.get(col, 0.0)))
        for param, col in STRUCTURE_PARAM_MAP.items()
    ]
    return jsonify({
        'fields': fields,
        'note': '有 DFT 结构描述子时填入真实值可显著提升预测可信度；留空则用训练集均值（模型对此敏感，见 L1-SHAP）',
    })


@app.route('/api/data/export', methods=['GET'])
def export_data():
    """导出数据集

    参数:
        format: 导出格式，支持 'csv' 或 'json'
    """
    if not model_state['is_initialized']:
        initialize_models()

    format = request.args.get('format', 'csv').lower()
    df = model_state['data']

    if format == 'json':
        # 导出为JSON
        data = df.to_dict('records')
        return jsonify({
            'data': data,
            'total_samples': len(data)
        })
    elif format == 'csv':
        # 导出为CSV
        import io
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)

        from flask import make_response
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=perovskite_data.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response
    else:
        return jsonify({'error': 'Unsupported format. Use csv or json.'}), 400


@app.route('/api/predict/batch', methods=['POST'])
def batch_predict():
    """批量预测带隙

    请求体:
    {
        "structures": [
            {
                "a_site": "Cs",
                "b_site": "Pb",
                "cl_ratio": 1.0,
                "br_ratio": 1.0,
                "i_ratio": 1.0
            },
            ...
        ]
    }
    """
    if not model_state['is_initialized']:
        initialize_models()

    data = request.get_json()
    structures = data.get('structures', [])

    if not structures:
        return jsonify({'error': 'No structures provided'}), 400

    results = []
    for struct in structures:
        try:
            a_site = struct.get('a_site', 'Cs')
            b_site = struct.get('b_site', 'Pb')
            cl_ratio = float(struct.get('cl_ratio', 0))
            br_ratio = float(struct.get('br_ratio', 0))
            i_ratio = float(struct.get('i_ratio', 0))

            # 构建特征
            temp_df = pd.DataFrame([{
                'Formula': f"{a_site}{b_site}Cl_{cl_ratio}Br_{br_ratio}I_{i_ratio}",
                'A_site': a_site,
                'B_site': b_site,
                'Cl_ratio': cl_ratio,
                'Br_ratio': br_ratio,
                'I_ratio': i_ratio,
                'Band Gap (eV)': 0  # 占位符
            }])

            # 结构描述子：优先用该条结构传入的真实值，缺省回退训练集列均值
            for col, val in structure_values_from_request(struct).items():
                temp_df[col] = val

            X, _, _ = model_state['preprocessor'].create_feature_matrix(temp_df, include_target=False)
            X_scaled = model_state['feature_engineer'].transform(X)

            # 预测：HSErel_SOC = PBE 基线 + Δ 修正
            predictor = model_state['predictor']
            if hasattr(predictor, 'predict_components'):
                pbe_pred, delta_pred, _ = predictor.predict_components(X_scaled)
            else:
                pbe_pred = predictor.predict(X_scaled)
                delta_pred = np.zeros_like(pbe_pred)
            override = struct.get('pbe_bandgap', None)
            pbe_base = np.array([float(override)]) if override is not None else pbe_pred
            hse_pred = pbe_base + delta_pred

            results.append({
                'input': struct,
                'formula': f"{a_site}{b_site}(Cl_{cl_ratio}Br_{br_ratio}I_{i_ratio})",
                'predicted_bandgap': float(hse_pred[0]),
                'bandgap_basis': 'HSErel_SOC (PBE + Δ-learning)',
                'pbe_source': 'provided' if override is not None else 'predicted',
                'pbe_bandgap': float(pbe_base[0]),
                'delta_correction': float(delta_pred[0])
            })

        except Exception as e:
            results.append({
                'input': struct,
                'error': str(e)
            })

    return jsonify({
        'results': results,
        'total': len(results),
        'success': sum(1 for r in results if 'error' not in r)
    })


# ==================== 启动应用 ====================

if __name__ == '__main__':
    print("Starting Perovskite Band Gap Prediction API...")
    initialize_models()
    app.run(host='0.0.0.0', port=5000, debug=True)
