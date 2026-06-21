"""Permutation-importance experiment implementation.

The experiment trains an XGBoost classifier without dominant demographic
predictors and estimates feature relevance through permutation importance. The
workflow is intentionally conservative about leakage by fitting preprocessing
inside each validation fold.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

from experiment_base import BaseExperiment


class PermutationImportanceExperiment(BaseExperiment):
    """Study 1: Feature importance isolating secondary lab variables by dropping demographic features."""

    def __init__(self) -> None:
        super().__init__("Permutation Importance Without Demographics")

    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        """Executes a stratified cross-validation tree training loop using runtime sampling caps."""
        df: pd.DataFrame = data.copy()

        max_samples: int = int(config.get("permutation_max_samples", 2000))
        max_splits: int = int(config.get("permutation_max_splits", 2))
        repeats: int = int(config.get("permutation_repeats", 1))
        estimators: int = int(config.get("permutation_estimators", 10))
        target_col: str = str(config.get("permutation_target_column", "ana_dura"))
        positive_label: str = str(config.get("permutation_positive_label", "Buscada negativo"))
        negative_label: str = str(config.get("permutation_negative_label", "Buscada positivo"))

        if target_col not in df.columns:
            raise ValueError(f"Permutation importance requires the target column '{target_col}'.")

        df[target_col] = df[target_col].astype("string")
        df = df[df[target_col].isin([positive_label, negative_label])].reset_index(drop=True)
        if df.empty:
            raise ValueError("No rows matched the requested positive/negative labels for permutation importance.")
        if df[target_col].nunique(dropna=False) < 2:
            raise ValueError("Permutation importance requires two target classes after filtering.")

        if len(df) > max_samples:
            total_rows = len(df)
            df = (
                df.groupby(target_col, group_keys=False)
                .apply(
                    lambda frame: frame.sample(
                        n=max(1, int(round(max_samples * len(frame) / total_rows))),
                        random_state=42,
                    )
                )
                .reset_index(drop=True)
            )
            if len(df) > max_samples:
                df = df.sample(n=max_samples, random_state=42).reset_index(drop=True)

        excluded_features: List[str] = ["sexo", "edad", "edadC", "sex", "id_pacie", target_col]
        features: List[str] = [col for col in df.columns if col not in excluded_features]
        if not features:
            raise ValueError("Permutation importance found no eligible predictor columns after exclusions.")

        X: pd.DataFrame = df[features].copy()
        y: np.ndarray = np.where(df[target_col] == positive_label, 1, 0)

        cat_cols: List[str] = X.select_dtypes(include=["object", "category", "string"]).columns.tolist()
        num_cols: List[str] = X.select_dtypes(include=[np.number]).columns.tolist()

        for column in cat_cols:
            X[column] = X[column].astype("string")
        for column in num_cols:
            X[column] = pd.to_numeric(X[column], errors="coerce").astype(float)

        preprocessor: ColumnTransformer = ColumnTransformer(
            transformers=[
                (
                    "cat",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="constant", fill_value="Missing")),
                            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                        ]
                    ),
                    cat_cols,
                ),
                (
                    "num",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="median")),
                        ]
                    ),
                    num_cols,
                ),
            ]
        )

        X_trans: np.ndarray = preprocessor.fit_transform(X)
        feature_names: np.ndarray = preprocessor.get_feature_names_out()

        class_counts = np.bincount(y)
        smallest_class = int(class_counts.min()) if len(class_counts) > 1 else 0
        n_splits = min(max_splits, smallest_class)
        if n_splits < 2:
            raise ValueError("Permutation importance requires at least two samples per class.")
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        importances: List[np.ndarray] = []

        for train_idx, test_idx in skf.split(X_trans, y):
            X_train, X_test = X_trans[train_idx], X_trans[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            model = XGBClassifier(
                n_estimators=estimators,
                max_depth=4,
                random_state=42,
                eval_metric="logloss",
                n_jobs=-1,
            )
            model.fit(X_train, y_train)

            result = permutation_importance(model, X_test, y_test, n_repeats=repeats, random_state=42, n_jobs=-1)
            importances.append(result.importances_mean)

        mean_importances: np.ndarray = np.mean(importances, axis=0)
        results_df: pd.DataFrame = pd.DataFrame({"Feature": feature_names, "Importance": mean_importances})
        results_df = results_df.sort_values(by="Importance", ascending=False).head(10)

        self.latex_table = results_df.to_latex(
            index=False,
            caption=f"Top Predictors for {target_col} via Permutation Importance",
            label="tab:perm_imp",
        )
        self.plotly_figure = px.bar(
            results_df,
            x="Importance",
            y="Feature",
            orientation="h",
            title=f"Permutation Importance for {target_col} (Excluding Demographics)",
        )
        self.plotly_figure.update_layout(yaxis={"categoryorder": "total ascending"})
