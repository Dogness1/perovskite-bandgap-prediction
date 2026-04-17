"""
对比分析模块
对生成结构与数据集结构进行对比分析
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from scipy import stats


class StructureComparator:
    """结构对比分析器"""

    def __init__(self, dataset_df: pd.DataFrame = None):
        """
        初始化对比器

        Args:
            dataset_df: 数据集DataFrame
        """
        self.dataset_df = dataset_df

    def compare_with_dataset(
        self,
        generated_structure: Dict,
        comparison_metrics: List[str] = None
    ) -> Dict:
        """
        将生成结构与数据集中的类似结构进行对比

        Args:
            generated_structure: 生成的结构信息
            comparison_metrics: 对比指标列表

        Returns:
            Dict: 对比结果
        """
        if comparison_metrics is None:
            comparison_metrics = ['bandgap', 'slme', 'stability']

        results = {
            'generated': generated_structure,
            'similar_in_dataset': [],
            'comparison': {}
        }

        if self.dataset_df is None:
            return results

        # 查找数据集中类似的结构（相同A位和B位）
        a_site = generated_structure.get('A_site')
        b_site = generated_structure.get('B_site')

        # 解析数据集中的化学式
        similar_mask = self.dataset_df['Formula'].str.startswith(f"{a_site}{b_site}")
        similar_structures = self.dataset_df[similar_mask]

        if len(similar_structures) > 0:
            results['similar_in_dataset'] = similar_structures[['Formula', 'Band Gap (eV)', 'SLME @ 5um']].to_dict('records')

            # 统计对比
            if 'bandgap' in comparison_metrics:
                dataset_bandgaps = similar_structures['Band Gap (eV)'].values
                gen_bandgap = generated_structure.get('predicted_bandgap', 0)

                results['comparison']['bandgap'] = {
                    'generated': gen_bandgap,
                    'dataset_mean': float(dataset_bandgaps.mean()),
                    'dataset_std': float(dataset_bandgaps.std()),
                    'dataset_min': float(dataset_bandgaps.min()),
                    'dataset_max': float(dataset_bandgaps.max()),
                    'percentile': float(stats.percentileofscore(dataset_bandgaps, gen_bandgap))
                }

            if 'slme' in comparison_metrics and len(similar_structures) > 0:
                # 估算生成结构的SLME（基于带隙的简单估算）
                gen_slme = self._estimate_slme(gen_bandgap) if 'bandgap' in results['comparison'] else 0
                dataset_slme = similar_structures['SLME @ 5um'].values

                results['comparison']['slme'] = {
                    'generated_estimated': gen_slme,
                    'dataset_mean': float(dataset_slme.mean()),
                    'dataset_max': float(dataset_slme.max())
                }

        return results

    def _estimate_slme(self, bandgap: float) -> float:
        """
        基于带隙估算SLME

        简化的经验模型：最优带隙约1.3-1.5 eV时SLME最高
        """
        # 使用简单的抛物线模型
        optimal_bandgap = 1.4
        max_slme = 0.25
        slme = max_slme * np.exp(-((bandgap - optimal_bandgap) ** 2) / 2)
        return float(slme)

    def analyze_halogen_trends(self, df: pd.DataFrame) -> Dict:
        """
        分析卤素对带隙的影响趋势

        Args:
            df: 数据集DataFrame

        Returns:
            Dict: 趋势分析结果
        """
        import re

        # 解析卤素比例
        def parse_halogen(formula):
            result = {'Cl': 0, 'Br': 0, 'I': 0}
            for h in ['Cl', 'Br', 'I']:
                match = re.search(rf'{h}_(\d+\.?\d*)', str(formula))
                if match:
                    result[h] = float(match.group(1))
            return result

        halogen_data = df['Formula'].apply(parse_halogen)
        halogen_df = pd.DataFrame(halogen_data.tolist())

        combined = pd.concat([df.reset_index(drop=True), halogen_df], axis=1)

        # 计算加权卤素指数
        combined['halogen_index'] = (
            combined['Cl'] * 1.81 +  # Cl半径
            combined['Br'] * 1.96 +  # Br半径
            combined['I'] * 2.20     # I半径
        ) / 3.0

        # 相关性分析
        correlation = combined['halogen_index'].corr(combined['Band Gap (eV)'])

        # 分组统计
        trends = {
            'correlation_halogen_radius_bandgap': round(correlation, 4),
            'by_halogen_type': {},
            'by_halogen_ratio': {}
        }

        # 按主卤素类型分组
        for h in ['Cl', 'Br', 'I']:
            mask = combined[h] > 2.0
            if mask.any():
                subset = combined[mask]
                trends['by_halogen_type'][h] = {
                    'mean_bandgap': float(subset['Band Gap (eV)'].mean()),
                    'mean_slme': float(subset['SLME @ 5um'].mean()),
                    'count': int(len(subset))
                }

        return trends

    def generate_comparison_report(
        self,
        generated_structures: List[Dict],
        output_format: str = 'dict'
    ) -> Dict:
        """
        生成对比分析报告

        Args:
            generated_structures: 生成的结构列表
            output_format: 输出格式

        Returns:
            Dict: 分析报告
        """
        report = {
            'summary': {
                'total_generated': len(generated_structures),
                'avg_predicted_bandgap': np.mean([s.get('predicted_bandgap', 0) for s in generated_structures]),
                'avg_stability_score': np.mean([s.get('stability_score', 0) for s in generated_structures])
            },
            'structures': generated_structures,
            'recommendations': []
        }

        # 生成推荐
        for s in generated_structures:
            if s.get('stability_score', 0) > 0.7:
                report['recommendations'].append({
                    'formula': s.get('formula'),
                    'reason': f"高稳定性 (score={s.get('stability_score'):.2f})，预测带隙 {s.get('predicted_bandgap'):.2f} eV"
                })

        return report


if __name__ == '__main__':
    print("StructureComparator module loaded successfully")
