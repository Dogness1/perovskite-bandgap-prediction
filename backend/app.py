"""
Flask API 主应用
三维钙钛矿卤素调控与带隙预测系统后端API
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

from data.preprocessor import PerovskitePreprocessor, load_data
from data.feature_engineer import FeatureEngineer, prepare_train_test_data
from models.predictor import BandGapPredictor
from models.generator import HalogenStructureGenerator
from analysis.comparator import StructureComparator

app = Flask(__name__)
CORS(app)

# 全局变量存储模型和数据
model_state = {
    'predictor': None,
    'generator': None,
    'preprocessor': None,
    'data': None,
    'feature_engineer': None,
    'is_initialized': False
}


def initialize_models():
    """初始化模型和数据"""
    if model_state['is_initialized']:
        return

    print("Initializing models...")

    # 加载数据
    data_path = os.path.join(os.path.dirname(__file__), '..', 'd3dd00015j2', 'perovs_data_final.xlsx')
    if os.path.exists(data_path):
        model_state['data'] = load_data(data_path)
        print(f"Data loaded: {len(model_state['data'])} samples")
    else:
        print(f"Warning: Data file not found at {data_path}")
        return

    # 初始化预处理器
    model_state['preprocessor'] = PerovskitePreprocessor()

    # 解析数据并创建特征
    df_parsed = model_state['preprocessor'].extract_features(model_state['data'])
    X, y, feature_names = model_state['preprocessor'].create_feature_matrix(df_parsed, include_target=True)

    # 初始化特征工程
    model_state['feature_engineer'] = FeatureEngineer()
    X_scaled = model_state['feature_engineer'].fit_transform(X, feature_names)

    # 清理数据：处理 NaN 和无穷大值
    X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=1e6, neginf=-1e6)
    y = np.nan_to_num(y, nan=0.0, posinf=1e6, neginf=-1e6)

    # 划分数据
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    # 训练预测模型
    model_state['predictor'] = BandGapPredictor(model_type='random_forest')
    model_state['predictor'].train(X_train, y_train, feature_names=feature_names)

    # 评估模型
    metrics = model_state['predictor'].evaluate(X_test, y_test)
    print(f"Model trained: R² = {metrics['r2']:.4f}, MAE = {metrics['mae']:.4f} eV")

    # 初始化生成器
    model_state['generator'] = HalogenStructureGenerator(
        predictor=model_state['predictor'],
        preprocessor=model_state['preprocessor']
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
    import re
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

        # 添加结构特征（使用默认值）
        default_cols = [
            'Deviation of Cubicity b axis',
            'Deviation of Cubicity c axis',
            'Deviation of Cubicity at alpha',
            'Deviation of Cubicity at beta',
            'Deviation of Cubicity at gamma',
            'Octaehdral Factor',
            'Tolerance Factor',
            "Bartel's Tolerance Factor"
        ]
        for col in default_cols:
            temp_df[col] = 0.01  # 默认值

        X, _, _ = model_state['preprocessor'].create_feature_matrix(temp_df, include_target=False)
        X_scaled = model_state['feature_engineer'].transform(X)

        # 预测
        prediction = model_state['predictor'].predict(X_scaled)

        result = {
            'formula': f"{a_site}{b_site}(Cl_{cl_ratio}Br_{br_ratio}I_{i_ratio})",
            'predicted_bandgap': float(prediction[0]),
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

            # 添加结构特征（使用默认值）
            default_cols = [
                'Deviation of Cubicity b axis',
                'Deviation of Cubicity c axis',
                'Deviation of Cubicity at alpha',
                'Deviation of Cubicity at beta',
                'Deviation of Cubicity at gamma',
                'Octaehdral Factor',
                'Tolerance Factor',
                "Bartel's Tolerance Factor"
            ]
            for col in default_cols:
                temp_df[col] = 0.01  # 默认值

            X, _, _ = model_state['preprocessor'].create_feature_matrix(temp_df, include_target=False)
            X_scaled = model_state['feature_engineer'].transform(X)

            # 预测
            prediction = model_state['predictor'].predict(X_scaled)

            results.append({
                'input': struct,
                'formula': f"{a_site}{b_site}(Cl_{cl_ratio}Br_{br_ratio}I_{i_ratio})",
                'predicted_bandgap': float(prediction[0])
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
