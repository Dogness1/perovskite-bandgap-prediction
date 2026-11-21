"""
结构生成模型模块
基于规则约束生成新的卤素混合钙钛矿结构
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy.stats import qmc
import re


class HalogenStructureGenerator:
    """卤素混合结构生成器"""

    # 卤素离子半径
    HALOGEN_RADII = {
        'Cl': 1.81,
        'Br': 1.96,
        'I': 2.20
    }

    # 基于数据集统计的卤素比例-带隙映射规则
    BANDGAP_HALOGEN_RULES = {
        'low': {      # < 1.5 eV
            'target_range': (0.0, 1.5),
            'Cl_range': (0, 0.5),
            'Br_range': (0, 1.0),
            'I_range': (1.5, 3.0)
        },
        'medium_low': {  # 1.5-2.5 eV
            'target_range': (1.5, 2.5),
            'Cl_range': (0, 1.0),
            'Br_range': (0.5, 2.0),
            'I_range': (0.5, 2.0)
        },
        'medium_high': {  # 2.5-3.5 eV
            'target_range': (2.5, 3.5),
            'Cl_range': (0.5, 2.0),
            'Br_range': (0.5, 2.0),
            'I_range': (0, 1.0)
        },
        'high': {     # > 3.5 eV
            'target_range': (3.5, 6.0),
            'Cl_range': (1.5, 3.0),
            'Br_range': (0, 1.0),
            'I_range': (0, 0.5)
        }
    }

    def __init__(self, predictor=None, preprocessor=None,
                 feature_engineer=None, structure_defaults=None):
        """
        初始化生成器

        Args:
            predictor: 已训练的带隙预测模型（DeltaCorrectedPredictor）
            preprocessor: 数据预处理器
            feature_engineer: 已拟合的 FeatureEngineer，用于按训练口径缩放特征
            structure_defaults: dict，8 个结构描述子的默认填充值（训练集列均值）
        """
        self.predictor = predictor
        self.preprocessor = preprocessor
        self.feature_engineer = feature_engineer
        self.structure_defaults = structure_defaults or {}

    def _get_target_category(self, target_bandgap: float) -> str:
        """根据目标带隙获取分类"""
        if target_bandgap < 1.5:
            return 'low'
        elif target_bandgap < 2.5:
            return 'medium_low'
        elif target_bandgap < 3.5:
            return 'medium_high'
        else:
            return 'high'

    def _calculate_tolerance_factor(self, a_radius: float, b_radius: float, halogen_radius: float) -> float:
        """
        计算Goldschmidt容差因子

        t = (r_A + r_X) / sqrt(2) * (r_B + r_X)

        Args:
            a_radius: A位离子半径
            b_radius: B位离子半径
            halogen_radius: 卤素离子半径

        Returns:
            float: 容差因子
        """
        return (a_radius + halogen_radius) / (np.sqrt(2) * (b_radius + halogen_radius))

    def _calculate_stability_score(self, tolerance_factor: float) -> float:
        """
        计算结构稳定性评分

        稳定结构: t ∈ [0.8, 1.05]

        Args:
            tolerance_factor: 容差因子

        Returns:
            float: 稳定性评分 (0-1)
        """
        if 0.8 <= tolerance_factor <= 1.05:
            # 在稳定范围内，越接近1越好
            return 1.0 - abs(tolerance_factor - 0.9) * 2
        elif 0.7 <= tolerance_factor < 0.8 or 1.05 < tolerance_factor <= 1.15:
            # 在边缘区域
            return 0.5
        else:
            # 不稳定
            return 0.0

    def _generate_halogen_ratios(
        self,
        target_bandgap: float,
        n_samples: int = 100,
        tolerance: float = 0.5
    ) -> List[Tuple[float, float, float]]:
        """
        生成卤素比例候选

        Args:
            target_bandgap: 目标带隙
            n_samples: 采样数量
            tolerance: 带隙容差

        Returns:
            List of (Cl_ratio, Br_ratio, I_ratio)
        """
        category = self._get_target_category(target_bandgap)
        rules = self.BANDGAP_HALOGEN_RULES[category]

        # 使用拉丁超立方采样
        sampler = qmc.LatinHypercube(d=3)
        samples = sampler.random(n=n_samples)

        # 将采样映射到卤素比例范围
        cl_range = rules['Cl_range']
        br_range = rules['Br_range']
        i_range = rules['I_range']

        candidates = []
        for sample in samples:
            cl = cl_range[0] + sample[0] * (cl_range[1] - cl_range[0])
            br = br_range[0] + sample[1] * (br_range[1] - br_range[0])
            i = i_range[0] + sample[2] * (i_range[1] - i_range[0])

            # 归一化，使总和为3
            total = cl + br + i
            if total > 0:
                cl = cl / total * 3
                br = br / total * 3
                i = i / total * 3
                candidates.append((round(cl, 3), round(br, 3), round(i, 3)))

        return candidates

    def generate(
        self,
        a_site: str,
        b_site: str,
        target_bandgap: float,
        n_samples: int = 10,
        bandgap_tolerance: float = 0.3
    ) -> List[Dict]:
        """
        生成新的卤素混合结构

        Args:
            a_site: A位阳离子 (如 'Cs', 'MA', 'FA')
            b_site: B位金属 (如 'Pb', 'Sn', 'Ge')
            target_bandgap: 目标带隙 (eV)
            n_samples: 返回的最大样本数
            bandgap_tolerance: 带隙容差 (eV)

        Returns:
            List of generated structures with predicted properties
        """
        # 生成候选卤素比例
        candidates = self._generate_halogen_ratios(target_bandgap, n_samples=200)

        results = []
        for cl, br, i in candidates:
            # 构建特征用于预测
            structure = {
                'A_site': a_site,
                'B_site': b_site,
                'Cl_ratio': cl,
                'Br_ratio': br,
                'I_ratio': i,
                'formula': self._format_formula(a_site, b_site, cl, br, i)
            }

            # 计算平均卤素半径
            avg_halogen_radius = (
                cl * self.HALOGEN_RADII['Cl'] +
                br * self.HALOGEN_RADII['Br'] +
                i * self.HALOGEN_RADII['I']
            ) / 3.0

            # 计算稳定性评分
            a_radius = self.preprocessor.ION_RADII.get(a_site, 1.5) if self.preprocessor else 1.5
            b_radius = self.preprocessor.ION_RADII.get(b_site, 1.0) if self.preprocessor else 1.0

            tolerance_factor = self._calculate_tolerance_factor(a_radius, b_radius, avg_halogen_radius)
            stability_score = self._calculate_stability_score(tolerance_factor)

            structure['tolerance_factor'] = round(tolerance_factor, 4)
            structure['stability_score'] = round(stability_score, 4)
            structure['avg_halogen_radius'] = round(avg_halogen_radius, 4)

            # 使用预测模型预测带隙
            if self.predictor and self.preprocessor:
                predicted_bandgap = self._predict_bandgap(structure)
                structure['predicted_bandgap'] = round(predicted_bandgap, 4)
            else:
                # 使用启发式估计
                structure['predicted_bandgap'] = self._heuristic_bandgap_estimate(cl, br, i)

            results.append(structure)

        # 筛选在目标带隙范围内的结构
        filtered = [
            r for r in results
            if abs(r['predicted_bandgap'] - target_bandgap) <= bandgap_tolerance
        ]

        # 如果没有满足条件的，放宽条件
        if not filtered:
            filtered = sorted(results, key=lambda x: abs(x['predicted_bandgap'] - target_bandgap))[:n_samples]

        # 按稳定性评分和带隙接近度排序
        filtered.sort(key=lambda x: (
            abs(x['predicted_bandgap'] - target_bandgap),
            -x['stability_score']
        ))

        return filtered[:n_samples]

    def _format_formula(self, a_site: str, b_site: str, cl: float, br: float, i: float) -> str:
        """格式化化学式"""
        parts = []
        if cl > 0.001:
            parts.append(f"Cl_{cl:.3f}")
        if br > 0.001:
            parts.append(f"Br_{br:.3f}")
        if i > 0.001:
            parts.append(f"I_{i:.3f}")
        return f"{a_site}{b_site}" + "".join(parts)

    def _predict_bandgap(self, structure: Dict) -> float:
        """用已训练的 Δ-learning 预测器估计带隙。

        v2.0 缺陷：本方法虽接收 predictor，却始终返回启发式估计，导致
        /api/generate 输出的 predicted_bandgap 绕过模型口径（MD-005 still_open#1）。
        现在按与训练一致的特征链路构造输入并调用 predictor；若缺少任何依赖，
        才回退到启发式估计（保持本模块可独立运行）。
        """
        if self.predictor is not None and self.preprocessor is not None \
                and self.feature_engineer is not None:
            import pandas as pd
            row = {
                'Formula': structure.get('formula', ''),
                'A_site': structure['A_site'],
                'B_site': structure['B_site'],
                'Cl_ratio': structure['Cl_ratio'],
                'Br_ratio': structure['Br_ratio'],
                'I_ratio': structure['I_ratio'],
                'Band Gap (eV)': 0.0,
            }
            for col, val in self.structure_defaults.items():
                row[col] = val
            df = pd.DataFrame([row])
            X, _, _ = self.preprocessor.create_feature_matrix(df, include_target=False)
            X_scaled = self.feature_engineer.transform(X)
            if hasattr(self.predictor, 'predict'):
                pred = self.predictor.predict(X_scaled)
                return float(np.asarray(pred).reshape(-1)[0])
        # 依赖不全时回退启发式（独立运行 / 单测场景）
        return self._heuristic_bandgap_estimate(
            structure['Cl_ratio'],
            structure['Br_ratio'],
            structure['I_ratio']
        )

    def _heuristic_bandgap_estimate(self, cl: float, br: float, i: float) -> float:
        """
        启发式带隙估计

        基于数据集统计的卤素比例-带隙关系
        """
        # 使用加权平均估计
        # Cl -> ~3.26 eV, Br -> ~2.81 eV, I -> ~2.37 eV
        cl_contribution = cl / 3.0 * 3.26
        br_contribution = br / 3.0 * 2.81
        i_contribution = i / 3.0 * 2.37

        base_bandgap = cl_contribution + br_contribution + i_contribution

        # 考虑混合效应（混合卤素通常有非线性效应）
        n_halogen_types = sum(1 for x in [cl, br, i] if x > 0.1)
        mixing_effect = 0.1 * (n_halogen_types - 1) if n_halogen_types > 1 else 0

        return base_bandgap + mixing_effect

    def analyze_halogen_effect(self, df: pd.DataFrame) -> Dict:
        """
        分析卤素对带隙的影响

        Args:
            df: 数据集DataFrame

        Returns:
            Dict: 分析结果
        """
        results = {
            'single_halogen': {},
            'mixed_halogen': {},
            'correlation': {}
        }

        # 解析化学式
        parsed = df['Formula'].apply(self._parse_formula_simple)
        parsed_df = pd.DataFrame(parsed.tolist())
        combined = pd.concat([df.reset_index(drop=True), parsed_df], axis=1)

        # 单卤素分析
        for halogen in ['Cl', 'Br', 'I']:
            mask = (combined[f'{halogen}_ratio'] > 2.5) & (combined['is_mixed_halogen'] == False)
            if mask.any():
                subset = combined[mask]
                results['single_halogen'][halogen] = {
                    'count': len(subset),
                    'mean_bandgap': round(subset['Band Gap (eV)'].mean(), 3),
                    'std_bandgap': round(subset['Band Gap (eV)'].std(), 3),
                    'min_bandgap': round(subset['Band Gap (eV)'].min(), 3),
                    'max_bandgap': round(subset['Band Gap (eV)'].max(), 3)
                }

        # 混合卤素分析
        mask_mixed = combined['is_mixed_halogen'] == True
        if mask_mixed.any():
            mixed = combined[mask_mixed]
            results['mixed_halogen'] = {
                'count': len(mixed),
                'mean_bandgap': round(mixed['Band Gap (eV)'].mean(), 3),
                'std_bandgap': round(mixed['Band Gap (eV)'].std(), 3)
            }

        # 卤素比例与带隙的相关性
        for halogen in ['Cl', 'Br', 'I']:
            corr = combined[f'{halogen}_ratio'].corr(combined['Band Gap (eV)'])
            results['correlation'][halogen] = round(corr, 4)

        return results

    def _parse_formula_simple(self, formula: str) -> Dict:
        """简化的化学式解析"""
        result = {'Cl_ratio': 0.0, 'Br_ratio': 0.0, 'I_ratio': 0.0, 'is_mixed_halogen': False}

        formula = str(formula)
        halogen_count = 0

        for halogen in ['Cl', 'Br', 'I']:
            pattern = rf'{halogen}_(\d+\.?\d*)'
            match = re.search(pattern, formula)
            if match:
                result[f'{halogen}_ratio'] = float(match.group(1))
                halogen_count += 1

        result['is_mixed_halogen'] = halogen_count > 1
        return result


if __name__ == '__main__':
    generator = HalogenStructureGenerator()

    # 测试生成
    results = generator.generate('Cs', 'Pb', target_bandgap=1.8, n_samples=5)
    print("Generated structures:")
    for r in results:
        print(f"  {r['formula']}: Band Gap = {r['predicted_bandgap']} eV, Stability = {r['stability_score']}")
