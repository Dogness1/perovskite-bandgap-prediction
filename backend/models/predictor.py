"""
带隙预测模型模块
支持 XGBoost / RandomForest / GradientBoosting；v2.0 默认口径为 RandomForest。
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score, GridSearchCV, KFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
import joblib
import os
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')


class BandGapPredictor:
    """带隙预测器"""

    def __init__(self, model_type: str = 'xgboost'):
        """
        初始化预测器

        Args:
            model_type: 模型类型，'xgboost', 'random_forest', 'gradient_boosting'
        """
        self.model_type = model_type
        self.model = None
        self.is_trained = False
        self.feature_names = None
        self.scaler = None
        self.cv_scores = None

    def _create_model(self, **kwargs):
        """创建模型实例"""
        if self.model_type == 'xgboost':
            if not XGBOOST_AVAILABLE:
                print("Warning: XGBoost not available, falling back to Random Forest")
                self.model_type = 'random_forest'
                return RandomForestRegressor(
                    n_estimators=kwargs.get('n_estimators', 200),
                    max_depth=kwargs.get('max_depth', 10),
                    random_state=kwargs.get('random_state', 42),
                    n_jobs=-1
                )
            return xgb.XGBRegressor(
                n_estimators=kwargs.get('n_estimators', 200),
                max_depth=kwargs.get('max_depth', 6),
                learning_rate=kwargs.get('learning_rate', 0.1),
                subsample=kwargs.get('subsample', 0.8),
                colsample_bytree=kwargs.get('colsample_bytree', 0.8),
                random_state=kwargs.get('random_state', 42),
                n_jobs=-1
            )
        elif self.model_type == 'random_forest':
            return RandomForestRegressor(
                n_estimators=kwargs.get('n_estimators', 200),
                max_depth=kwargs.get('max_depth', 10),
                random_state=kwargs.get('random_state', 42),
                n_jobs=-1
            )
        elif self.model_type == 'gradient_boosting':
            return GradientBoostingRegressor(
                n_estimators=kwargs.get('n_estimators', 200),
                max_depth=kwargs.get('max_depth', 6),
                learning_rate=kwargs.get('learning_rate', 0.1),
                random_state=kwargs.get('random_state', 42)
            )
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        feature_names: list = None,
        tune_hyperparameters: bool = False,
        sample_weight: np.ndarray = None,
        cv_repeats: int = 1,
        compute_cv: bool = True,
        **kwargs
    ) -> Dict:
        """
        训练模型

        Args:
            X_train: 训练特征 (n_train, d)
            y_train: 训练目标 (n_train,)
            feature_names: 特征名称 (d,)
            tune_hyperparameters: 是否进行超参数调优
            sample_weight: 样本权重 (n_train,)，透传给 model.fit（RF/XGB 均支持）
            cv_repeats: 内部 CV 重复次数，>1 时改用 RepeatedKFold(5, cv_repeats)
            compute_cv: 是否计算内部 CV；批量离线训练（train.py 逐折训练）设 False 省时
            **kwargs: 模型参数

        Returns:
            dict: 训练结果
        """
        self.feature_names = feature_names

        if tune_hyperparameters:
            self.model = self._tune_hyperparameters(X_train, y_train)
        else:
            self.model = self._create_model(**kwargs)
            # 样本权重（导师文档3 的 10x10 卤素网格加权）在此透传；
            # 内部 CV 报告不传权重，避免 cross_val_score 的 fit_params 版本差异。
            if sample_weight is not None:
                self.model.fit(X_train, y_train, sample_weight=sample_weight)
            else:
                self.model.fit(X_train, y_train)

        # 交叉验证评估：默认单次 5 折；设为 10 即为 10x5 重复 CV。
        # compute_cv=False 供 train.py 的逐折训练使用，避免嵌套重复训练。
        if compute_cv:
            if cv_repeats > 1:
                from sklearn.model_selection import RepeatedKFold
                cv = RepeatedKFold(n_splits=5, n_repeats=cv_repeats, random_state=42)
            else:
                cv = KFold(n_splits=5, shuffle=True, random_state=42)
            self.cv_scores = cross_val_score(self.model, X_train, y_train, cv=cv, scoring='r2')
        else:
            self.cv_scores = None

        self.is_trained = True

        return {
            'cv_r2_mean': float(self.cv_scores.mean()) if self.cv_scores is not None else None,
            'cv_r2_std': float(self.cv_scores.std()) if self.cv_scores is not None else None,
            'model_type': self.model_type
        }

    def _tune_hyperparameters(self, X: np.ndarray, y: np.ndarray):
        """超参数调优"""
        if self.model_type == 'xgboost' and XGBOOST_AVAILABLE:
            param_grid = {
                'n_estimators': [100, 200, 300],
                'max_depth': [4, 6, 8],
                'learning_rate': [0.05, 0.1, 0.2],
                'subsample': [0.7, 0.8, 0.9],
                'colsample_bytree': [0.7, 0.8, 0.9]
            }
            base_model = xgb.XGBRegressor(random_state=42, n_jobs=-1)
        else:
            param_grid = {
                'n_estimators': [100, 200, 300],
                'max_depth': [6, 8, 10],
            }
            base_model = self._create_model()

        grid_search = GridSearchCV(
            base_model, param_grid, cv=5, scoring='r2', n_jobs=-1, verbose=0
        )
        grid_search.fit(X, y)

        print(f"Best parameters: {grid_search.best_params_}")
        print(f"Best CV R²: {grid_search.best_score_:.4f}")

        return grid_search.best_estimator_

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        预测带隙

        Args:
            X: 特征矩阵

        Returns:
            np.ndarray: 预测的带隙值
        """
        if not self.is_trained:
            raise ValueError("Model has not been trained. Call train() first.")

        return self.model.predict(X)

    def predict_with_uncertainty(self, X: np.ndarray, n_estimators: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """
        带不确定性估计的预测

        Args:
            X: 特征矩阵
            n_estimators: 用于估计不确定性的树的数量

        Returns:
            mean: 预测均值
            std: 预测标准差
        """
        if not self.is_trained:
            raise ValueError("Model has not been trained. Call train() first.")

        # 使用模型的预测方差
        if hasattr(self.model, 'predict'):
            predictions = self.model.predict(X)

            # 对于集成模型，估计不确定性
            if hasattr(self.model, 'estimators_'):
                all_preds = np.array([est.predict(X) for est in self.model.estimators_])
                std = np.std(all_preds, axis=0)
            else:
                # 使用交叉验证的R²作为不确定性的代理（未计算 CV 时用保守默认值）
                cv_r2 = float(self.cv_scores.mean()) if self.cv_scores is not None else 0.8
                std = predictions * (1 - cv_r2) * 0.1

            return predictions, std

        return self.predict(X), np.zeros(len(X))

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray,
                 groups: np.ndarray = None) -> Dict:
        """
        评估模型性能

        Args:
            X_test: 测试特征 (n_test, d)
            y_test: 测试目标 (n_test,)
            groups: 分组标签 (n_test,)，如 A_B 组合；给出时额外输出各组 MAE

        Returns:
            dict: 评估指标；有 groups 时含 'by_group'
        """
        y_pred = self.predict(X_test)
        result = {
            'r2': r2_score(y_test, y_pred),
            'mae': mean_absolute_error(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'mse': mean_squared_error(y_test, y_pred)
        }
        if groups is not None:
            groups = np.asarray(groups)
            result['by_group'] = {}
            for g in np.unique(groups):
                mask = groups == g
                if mask.sum() >= 2:
                    result['by_group'][str(g)] = {
                        'n': int(mask.sum()),
                        'mae': float(mean_absolute_error(y_test[mask], y_pred[mask])),
                    }
        return result

    def get_feature_importance(self) -> pd.DataFrame:
        """
        获取特征重要性

        Returns:
            pd.DataFrame: 特征重要性排序
        """
        if not self.is_trained:
            raise ValueError("Model has not been trained. Call train() first.")

        if hasattr(self.model, 'feature_importances_'):
            importance = self.model.feature_importances_
        else:
            raise ValueError("Model does not have feature_importances_ attribute")

        df_importance = pd.DataFrame({
            'feature': self.feature_names if self.feature_names else [f'feature_{i}' for i in range(len(importance))],
            'importance': importance
        }).sort_values('importance', ascending=False)

        return df_importance

    def save_model(self, filepath: str):
        """保存模型到文件"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({
            'model': self.model,
            'model_type': self.model_type,
            'is_trained': self.is_trained,
            'feature_names': self.feature_names,
            'cv_scores': self.cv_scores
        }, filepath)

    def load_model(self, filepath: str):
        """从文件加载模型"""
        data = joblib.load(filepath)
        self.model = data['model']
        self.model_type = data['model_type']
        self.is_trained = data['is_trained']
        self.feature_names = data['feature_names']
        self.cv_scores = data['cv_scores']


def train_and_evaluate_model(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    feature_names: list,
    model_type: str = 'xgboost',
    save_path: str = None
) -> Tuple[BandGapPredictor, Dict]:
    """
    训练并评估模型

    Args:
        X_train, X_test, y_train, y_test: 训练和测试数据
        feature_names: 特征名称
        model_type: 模型类型
        save_path: 模型保存路径

    Returns:
        model: 训练好的模型
        metrics: 评估指标
    """
    model = BandGapPredictor(model_type=model_type)

    # 训练
    train_result = model.train(X_train, y_train, feature_names=feature_names)
    print(f"Training result: CV R² = {train_result['cv_r2_mean']:.4f} ± {train_result['cv_r2_std']:.4f}")

    # 评估
    metrics = model.evaluate(X_test, y_test)
    print(f"Test R² = {metrics['r2']:.4f}, MAE = {metrics['mae']:.4f} eV, RMSE = {metrics['rmse']:.4f} eV")

    # 保存
    if save_path:
        model.save_model(save_path)
        print(f"Model saved to {save_path}")

    return model, metrics


if __name__ == '__main__':
    print("BandGapPredictor module loaded successfully")
