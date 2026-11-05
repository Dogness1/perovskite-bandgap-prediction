"""
数据预处理模块
解析钙钛矿化学式，提取A位、B位阳离子和卤素比例特征
"""

import re
import pandas as pd
import numpy as np
from typing import Dict, Tuple


class PerovskitePreprocessor:
    """钙钛矿数据预处理器"""

    # A位阳离子列表
    A_SITES = ['MA', 'FA', 'Cs', 'Rb', 'K', 'Na']

    # B位金属离子列表
    B_SITES = ['Ge', 'Sn', 'Pb', 'Ca', 'Sr', 'Ba', 'Cd', 'Zn', 'Mg', 'Cu', 'Ni', 'Fe', 'Mn', 'Co']

    # 卤素列表
    HALOGENS = ['Cl', 'Br', 'I']

    # 离子半径 (Angstrom)
    ION_RADII = {
        # A位
        'MA': 2.17, 'FA': 2.53, 'Cs': 1.67, 'Rb': 1.52, 'K': 1.38, 'Na': 1.02,
        # B位
        'Ge': 0.73, 'Sn': 0.93, 'Pb': 1.19, 'Ca': 1.00, 'Sr': 1.18, 'Ba': 1.35,
        'Cd': 0.95, 'Zn': 0.74, 'Mg': 0.72, 'Cu': 0.73, 'Ni': 0.69, 'Fe': 0.78, 'Mn': 0.83, 'Co': 0.745,
        # 卤素
        'Cl': 1.81, 'Br': 1.96, 'I': 2.20
    }

    def __init__(self):
        self.feature_columns = None

    def parse_formula(self, formula: str) -> Dict:
        """
        解析化学式，提取组成信息

        Args:
            formula: 化学式，如 'CsPbI_0.75Br_2.25' 或 'MAPbI_3'

        Returns:
            dict: 包含A位、B位、卤素比例的字典
        """
        result = {
            'A_site': None,
            'B_site': None,
            'Cl_ratio': 0.0,
            'Br_ratio': 0.0,
            'I_ratio': 0.0,
            'is_mixed_halogen': False
        }

        formula = str(formula).strip()

        # 1. 提取A位阳离子
        for a_site in sorted(self.A_SITES, key=len, reverse=True):
            if formula.startswith(a_site):
                result['A_site'] = a_site
                formula = formula[len(a_site):]
                break

        # 2. 提取B位金属
        for b_site in sorted(self.B_SITES, key=len, reverse=True):
            if formula.startswith(b_site):
                result['B_site'] = b_site
                formula = formula[len(b_site):]
                break

        # 3.5 回退解析：混合 A 位化学式（如 K_0.5Rb_0.125FA_0.375SrBr_3）
        # 前缀匹配会把 "K" 当 A 位、剩余串以下划线开头导致 B 位匹配失败，
        # 进而产生 B 位 one-hot 全 0 与 B_radius=NaN 的静默特征污染。
        # 原数据集有 31 个（11.0%）这样的样本。仅在前缀解析失败时启用。
        if result['B_site'] is None:
            b_alt = '|'.join(sorted(self.B_SITES, key=len, reverse=True))
            match_b = re.search(rf'({b_alt})(?=Cl|Br|I)', formula)
            if match_b:
                result['B_site'] = match_b.group(1)

        # 3. 提取卤素比例
        halogen_count = 0
        for halogen in self.HALOGENS:
            # 匹配卤素及其比例，如 I_0.75, Br_2.25, Cl_3
            pattern = rf'{halogen}_(\d+\.?\d*)'
            match = re.search(pattern, formula)
            if match:
                ratio = float(match.group(1))
                result[f'{halogen}_ratio'] = ratio
                halogen_count += 1
            else:
                # 检查是否有单独的卤素（如 MAPbI_3 中的 I_3）
                pattern_simple = rf'{halogen}_(\d+)'
                match_simple = re.search(pattern_simple, formula)
                if match_simple:
                    result[f'{halogen}_ratio'] = float(match_simple.group(1))
                    halogen_count += 1

        # 标记是否为混合卤素
        result['is_mixed_halogen'] = halogen_count > 1

        return result

    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        从DataFrame中提取特征

        Args:
            df: 原始数据DataFrame

        Returns:
            pd.DataFrame: 包含提取特征的新DataFrame
        """
        # 解析化学式
        parsed = df['Formula'].apply(self.parse_formula)
        parsed_df = pd.DataFrame(parsed.tolist())

        # 合并原始数据和解析结果
        result = pd.concat([df.reset_index(drop=True), parsed_df], axis=1)

        return result

    def create_feature_matrix(self, df: pd.DataFrame, include_target: bool = True) -> Tuple[np.ndarray, np.ndarray, list]:
        """
        创建用于机器学习的特征矩阵

        Args:
            df: 包含解析特征的DataFrame
            include_target: 是否包含目标变量

        Returns:
            X: 特征矩阵
            y: 目标变量 (如果include_target为True)
            feature_names: 特征名称列表
        """
        features = []

        # 1. A位One-hot编码
        a_site_dummies = pd.get_dummies(df['A_site'], prefix='A')
        for a_site in self.A_SITES:
            col = f'A_{a_site}'
            if col not in a_site_dummies.columns:
                a_site_dummies[col] = 0
        features.append(a_site_dummies[[f'A_{a}' for a in self.A_SITES]])

        # 2. B位One-hot编码
        b_site_dummies = pd.get_dummies(df['B_site'], prefix='B')
        for b_site in self.B_SITES:
            col = f'B_{b_site}'
            if col not in b_site_dummies.columns:
                b_site_dummies[col] = 0
        features.append(b_site_dummies[[f'B_{b}' for b in self.B_SITES]])

        # 3. 卤素比例
        features.append(df[['Cl_ratio', 'Br_ratio', 'I_ratio']])

        # 4. 离子半径特征
        df_copy = df.copy()
        df_copy['A_radius'] = df_copy['A_site'].map(self.ION_RADII)
        df_copy['B_radius'] = df_copy['B_site'].map(self.ION_RADII)
        # 计算平均卤素半径：按真实卤素总数做比例加权（原实现固定除以 3.0，
        # 当 Cl+Br+I != 3 时会算错；本数据集恒为 3，故指标不变，属正确性修复）
        halogen_total = (
            df_copy['Cl_ratio'] + df_copy['Br_ratio'] + df_copy['I_ratio']
        ).astype(float)
        weighted_radius = (
            df_copy['Cl_ratio'] * self.ION_RADII['Cl'] +
            df_copy['Br_ratio'] * self.ION_RADII['Br'] +
            df_copy['I_ratio'] * self.ION_RADII['I']
        )
        df_copy['avg_halogen_radius'] = np.divide(
            weighted_radius, halogen_total,
            out=np.zeros(len(df_copy), dtype=float),
            where=halogen_total.to_numpy() > 0,
        )
        features.append(df_copy[['A_radius', 'B_radius', 'avg_halogen_radius']])

        # 5. 结构特征（如果存在）
        structure_cols = [
            'Deviation of Cubicity b axis',
            'Deviation of Cubicity c axis',
            'Deviation of Cubicity at alpha',
            'Deviation of Cubicity at beta',
            'Deviation of Cubicity at gamma',
            'Octaehdral Factor',
            'Tolerance Factor',
            "Bartel's Tolerance Factor"
        ]
        existing_structure_cols = [col for col in structure_cols if col in df.columns]
        if existing_structure_cols:
            features.append(df[existing_structure_cols])

        # 合并所有特征
        X_df = pd.concat(features, axis=1)
        X = X_df.values
        feature_names = X_df.columns.tolist()

        self.feature_columns = feature_names

        if include_target and 'Band Gap (eV)' in df.columns:
            y = df['Band Gap (eV)'].values
            return X, y, feature_names
        else:
            return X, None, feature_names

    def get_available_elements(self, df: pd.DataFrame) -> Dict:
        """
        获取数据集中存在的元素种类

        Returns:
            dict: 包含A位、B位、卤素列表
        """
        parsed = self.extract_features(df)
        return {
            'A_sites': sorted(parsed['A_site'].dropna().unique().tolist()),
            'B_sites': sorted(parsed['B_site'].dropna().unique().tolist()),
            'halogens': self.HALOGENS
        }


def load_data(filepath: str) -> pd.DataFrame:
    """
    加载Excel数据文件

    Args:
        filepath: Excel文件路径

    Returns:
        pd.DataFrame: 数据DataFrame
    """
    return pd.read_excel(filepath)


if __name__ == '__main__':
    # 测试代码
    preprocessor = PerovskitePreprocessor()

    # 测试化学式解析
    test_formulas = ['CsPbI_0.75Br_2.25', 'MAPbI_3', 'FAGeBr_1.5Cl_1.5']
    for f in test_formulas:
        result = preprocessor.parse_formula(f)
        print(f"{f} -> {result}")
