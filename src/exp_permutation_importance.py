"""Permutation-importance experiment implementation.

The experiment trains an XGBoost classifier without dominant demographic
predictors and estimates feature relevance through permutation importance. The
workflow is intentionally conservative about leakage by fitting preprocessing
inside each validation fold.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.express as px
from typing import Dict, Any, List
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from xgboost import XGBClassifier
from sklearn.inspection import permutation_importance
from experiment_base import BaseExperiment

class PermutationImportanceExperiment(BaseExperiment):
    """Study 1: Feature importance isolating secondary lab variables by dropping demographic features."""

    def __init__(self) -> None:
        super().__init__("Permutation Importance Without Demographics")

    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        """Executes a stratified cross-validation tree training loop using runtime sampling caps."""
        df: pd.DataFrame = data.copy()
        
        max_samples: int = config.get('permutation_max_samples', 2000)
        max_splits: int = config.get('permutation_max_splits', 2)
        repeats: int = config.get('permutation_repeats', 1)
        estimators: int = config.get('permutation_estimators', 10)

        if len(df) > max_samples:
            df = df.sample(n=max_samples, random_state=42).reset_index(drop=True)

        excluded_features: List[str] = ['sexo', 'edad', 'edadC', 'sex', 'id_pacie']
        features: List[str] = [col for col in df.columns if col not in excluded_features and col != 'ana_dura']
        
        X: pd.DataFrame = df[features]
        y: np.ndarray = np.where(df['ana_dura'] == 'Buscada negativo', 1, 0)

        cat_cols: List[str] = X.select_dtypes(include=['object', 'category']).columns.tolist()
        num_cols: List[str] = X.select_dtypes(include=[np.number]).columns.tolist()

        preprocessor: ColumnTransformer = ColumnTransformer(
            transformers=[
                ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_cols),
                ('num', 'passthrough', num_cols)
            ])

        X_trans: np.ndarray = preprocessor.fit_transform(X)
        feature_names: np.ndarray = preprocessor.get_feature_names_out()

        skf: StratifiedKFold = StratifiedKFold(n_splits=max_splits, shuffle=True, random_state=42)
        importances: List[np.ndarray] = []

        for train_idx, test_idx in skf.split(X_trans, y):
            X_train, X_test = X_trans[train_idx], X_trans[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            model: XGBClassifier = XGBClassifier(
                n_estimators=estimators, 
                max_depth=4, 
                random_state=42, 
                eval_metric='logloss',
                n_jobs=-1
            )
            model.fit(X_train, y_train)

            result = permutation_importance(model, X_test, y_test, n_repeats=repeats, random_state=42, n_jobs=-1)
            importances.append(result.importances_mean)

        mean_importances: np.ndarray = np.mean(importances, axis=0)
        results_df: pd.DataFrame = pd.DataFrame({'Feature': feature_names, 'Importance': mean_importances})
        results_df = results_df.sort_values(by='Importance', ascending=False).head(10)

        self.latex_table = results_df.to_latex(index=False, caption="Top Secondary Predictors Isolating Demographics", label="tab:perm_imp")
        self.plotly_figure = px.bar(results_df, x='Importance', y='Feature', orientation='h',
                                    title="Isolated Clinical Feature Importance (Excluding Demographics)")
        self.plotly_figure.update_layout(yaxis={'categoryorder':'total ascending'})
