"""
特征工程模块
构建和转换用于机器学习的特征
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from typing import Tuple, Optional
import joblib
import os


class FeatureEngineer:
    """特征工程类"""

    def __init__(self, scaler_type: str = 'standard'):
        """
        初始化特征工程器

        Args:
            scaler_type: 标准化类型，'standard' 或 'minmax'
        """
        self.scaler_type = scaler_type
        self.scaler = StandardScaler() if scaler_type == 'standard' else MinMaxScaler()
        self.is_fitted = False
        self.feature_names = None

    def fit_transform(self, X: np.ndarray, feature_names: list = None) -> np.ndarray:
        """
        拟合并转换特征

        Args:
            X: 特征矩阵
            feature_names: 特征名称列表

        Returns:
            np.ndarray: 标准化后的特征矩阵
        """
        self.feature_names = feature_names
        X_scaled = self.scaler.fit_transform(X)
        self.is_fitted = True
        return X_scaled

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        转换特征（使用已拟合的scaler）

        Args:
            X: 特征矩阵

        Returns:
            np.ndarray: 标准化后的特征矩阵
        """
        if not self.is_fitted:
            raise ValueError("Scaler has not been fitted. Call fit_transform first.")
        return self.scaler.transform(X)

    def save_scaler(self, filepath: str):
        """保存scaler到文件"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({
            'scaler': self.scaler,
            'scaler_type': self.scaler_type,
            'is_fitted': self.is_fitted,
            'feature_names': self.feature_names
        }, filepath)

    def load_scaler(self, filepath: str):
        """从文件加载scaler"""
        data = joblib.load(filepath)
        self.scaler = data['scaler']
        self.scaler_type = data['scaler_type']
        self.is_fitted = data['is_fitted']
        self.feature_names = data['feature_names']


def prepare_train_test_data(
    df: pd.DataFrame,
    preprocessor,
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list]:
    """
    准备训练和测试数据

    Args:
        df: 原始数据DataFrame
        preprocessor: PerovskitePreprocessor实例
        test_size: 测试集比例
        random_state: 随机种子

    Returns:
        X_train, X_test, y_train, y_test, feature_names
    """
    # 提取特征
    df_parsed = preprocessor.extract_features(df)

    # 创建特征矩阵
    X, y, feature_names = preprocessor.create_feature_matrix(df_parsed, include_target=True)

    # 划分训练测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    return X_train, X_test, y_train, y_test, feature_names


def calculate_feature_importance(model, feature_names: list) -> pd.DataFrame:
    """
    计算特征重要性

    Args:
        model: 训练好的模型
        feature_names: 特征名称列表

    Returns:
        pd.DataFrame: 特征重要性排序
    """
    if hasattr(model, 'feature_importances_'):
        importance = model.feature_importances_
    elif hasattr(model, 'coef_'):
        importance = np.abs(model.coef_)
    else:
        raise ValueError("Model does not have feature_importances_ or coef_ attribute")

    df_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)

    return df_importance


def create_synthetic_features(X: np.ndarray, feature_names: list) -> Tuple[np.ndarray, list]:
    """
    创建合成特征（交叉特征）

    Args:
        X: 原始特征矩阵
        feature_names: 特征名称列表

    Returns:
        X_enhanced: 增强特征矩阵
        enhanced_names: 增强特征名称列表
    """
    enhanced_names = feature_names.copy()
    synthetic_features = []

    # 查找卤素比例特征的索引
    halogen_indices = {}
    for i, name in enumerate(feature_names):
        if name in ['Cl_ratio', 'Br_ratio', 'I_ratio']:
            halogen_indices[name] = i

    # 创建卤素比例交互特征
    if len(halogen_indices) >= 2:
        # Cl/Br 比值
        if 'Cl_ratio' in halogen_indices and 'Br_ratio' in halogen_indices:
            cl_idx = halogen_indices['Cl_ratio']
            br_idx = halogen_indices['Br_ratio']
            ratio = np.where(X[:, br_idx] != 0, X[:, cl_idx] / (X[:, br_idx] + 1e-6), 0)
            synthetic_features.append(ratio.reshape(-1, 1))
            enhanced_names.append('Cl_Br_ratio')

        # I/Cl 比值
        if 'I_ratio' in halogen_indices and 'Cl_ratio' in halogen_indices:
            i_idx = halogen_indices['I_ratio']
            cl_idx = halogen_indices['Cl_ratio']
            ratio = np.where(X[:, cl_idx] != 0, X[:, i_idx] / (X[:, cl_idx] + 1e-6), 0)
            synthetic_features.append(ratio.reshape(-1, 1))
            enhanced_names.append('I_Cl_ratio')

    # 合并特征
    if synthetic_features:
        X_enhanced = np.hstack([X] + synthetic_features)
    else:
        X_enhanced = X

    return X_enhanced, enhanced_names


if __name__ == '__main__':
    # 测试代码
    print("Feature Engineering module loaded successfully")
