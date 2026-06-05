"""Permutation-importance experiment implementation.

The experiment trains an XGBoost classifier without dominant demographic
predictors and estimates feature relevance through permutation importance. The
workflow is intentionally conservative about leakage by fitting preprocessing
inside each validation fold.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pandas as pd
import plotly.express as px
from sklearn.compose import ColumnTransformer
from sklearn.inspection import permutation_importance
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

from experiment_base import BaseExperiment

BinaryTarget = npt.NDArray[np.int_]


class PermutationImportanceExperiment(BaseExperiment):
    """Estimate feature importance after removing demographic shortcuts.

    Attributes:
        max_samples: Maximum number of rows used during the experiment.
        max_splits: Maximum number of stratified validation folds.
        n_repeats: Number of shuffling repeats per fold.
        n_estimators: Number of boosting trees in the classifier.
    """

    DEFAULT_MAX_SAMPLES = 1000
    DEFAULT_MAX_SPLITS = 2
    DEFAULT_N_REPEATS = 1
    DEFAULT_N_ESTIMATORS = 10

    def __init__(
        self,
        max_samples: int | None = None,
        max_splits: int | None = None,
        n_repeats: int | None = None,
        n_estimators: int | None = None,
    ) -> None:
        """Initialize experiment parameters.

        Args:
            max_samples: Optional cap on the number of sampled observations.
            max_splits: Optional cap on cross-validation folds.
            n_repeats: Optional number of permutation repeats per fold.
            n_estimators: Optional number of trees for the classifier.
        """
        super().__init__("Permutation Importance Without Demographics")
        self.max_samples: int = max_samples or self.DEFAULT_MAX_SAMPLES
        self.max_splits: int = max_splits or self.DEFAULT_MAX_SPLITS
        self.n_repeats: int = n_repeats or self.DEFAULT_N_REPEATS
        self.n_estimators: int = n_estimators or self.DEFAULT_N_ESTIMATORS

    def _sample_frame(
        self,
        frame: pd.DataFrame,
        target: BinaryTarget,
        sample_size: int,
    ) -> tuple[pd.DataFrame, BinaryTarget]:
        """Draw a stratified subsample when the dataset is too large.

        Args:
            frame: Feature matrix before preprocessing.
            target: Binary target aligned with ``frame``.
            sample_size: Upper bound on retained rows.

        Returns:
            Tuple containing the sampled dataframe and aligned target vector.
        """
        if len(frame) <= sample_size:
            return frame.reset_index(drop=True), target

        target_series = pd.Series(target, index=frame.index, name="_target")
        sampled_parts: list[pd.DataFrame] = []
        remaining = sample_size
        counts = target_series.value_counts()

        for label, count in counts.items():
            label_index = target_series[target_series == label].index
            label_frame = frame.loc[label_index]
            label_quota = max(1, round(count * sample_size / len(frame)))
            label_quota = min(label_quota, len(label_frame), remaining)
            sampled_parts.append(label_frame.sample(n=label_quota, random_state=42))
            remaining -= label_quota

        sampled = pd.concat(sampled_parts).sort_index()
        if len(sampled) < sample_size:
            extra = frame.drop(index=sampled.index).sample(
                n=sample_size - len(sampled),
                random_state=42,
            )
            sampled = pd.concat([sampled, extra]).sort_index()

        sampled_target = target_series.loc[sampled.index].to_numpy(dtype=int)
        return sampled.reset_index(drop=True), sampled_target

    def _normalize_predictors(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Normalize mixed-type predictors before model fitting.

        Args:
            frame: Predictor matrix selected for the experiment.

        Returns:
            Copy of the predictor matrix with categorical and numeric columns
            normalized for downstream preprocessing.
        """
        normalized = frame.copy()
        categorical_columns = normalized.select_dtypes(include=["object", "category"]).columns.tolist()
        numeric_columns = normalized.select_dtypes(include=[np.number]).columns.tolist()

        if categorical_columns:
            normalized[categorical_columns] = normalized[categorical_columns].astype(object)
            normalized[categorical_columns] = normalized[categorical_columns].where(
                normalized[categorical_columns].notna(),
                "Missing",
            ).astype(str)

        if numeric_columns:
            normalized[numeric_columns] = normalized[numeric_columns].replace([np.inf, -np.inf], np.nan)
            normalized[numeric_columns] = normalized[numeric_columns].fillna(normalized[numeric_columns].median())

        return normalized

    def run(self, data: pd.DataFrame) -> None:
        """Run the permutation-importance workflow.

        Args:
            data: Preprocessed clinical dataframe.

        Raises:
            ValueError: If the target column is missing or the dataset does not
                contain enough variability for stratified validation.
        """
        df = data.copy()

        if "ana_dura" not in df.columns:
            raise ValueError("Permutation importance requires the 'ana_dura' target column.")

        df = df[df["ana_dura"].notna()].copy()
        if df.empty:
            raise ValueError("Permutation importance requires non-null values in 'ana_dura'.")

        excluded_features = ["sexo", "edad", "edadC", "sex"]
        features = [column for column in df.columns if column not in excluded_features and column != "ana_dura"]
        if not features:
            raise ValueError("No predictor columns remain after excluding demographic fields and the target.")

        X = df[features].copy()
        y: BinaryTarget = np.where(df["ana_dura"] == "Buscada negativo", 1, 0).astype(int)

        class_counts = pd.Series(y).value_counts()
        if len(class_counts) < 2:
            raise ValueError("Permutation importance requires at least two target classes in 'ana_dura'.")

        X, y = self._sample_frame(X, y, self.max_samples)
        X = self._normalize_predictors(X)

        class_counts = pd.Series(y).value_counts()
        min_class_count = int(class_counts.min())
        if min_class_count < 2:
            raise ValueError(
                "Permutation importance requires at least two samples in each target class for stratified cross-validation."
            )

        categorical_columns = X.select_dtypes(include=["object", "category"]).columns.tolist()
        numeric_columns = X.select_dtypes(include=[np.number]).columns.tolist()
        n_splits = min(self.max_splits, min_class_count)
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        importance_frames: list[pd.Series] = []

        # Fit preprocessing inside each fold to avoid leaking test-fold information.
        for train_idx, test_idx in splitter.split(X, y):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            preprocessor = ColumnTransformer(
                transformers=[
                    ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_columns),
                    ("num", "passthrough", numeric_columns),
                ]
            )

            X_train_transformed = preprocessor.fit_transform(X_train)
            X_test_transformed = preprocessor.transform(X_test)
            feature_names = preprocessor.get_feature_names_out()

            model = XGBClassifier(
                n_estimators=self.n_estimators,
                max_depth=5,
                random_state=42,
                eval_metric="logloss",
            )
            model.fit(X_train_transformed, y_train)

            result = permutation_importance(
                model,
                X_test_transformed,
                y_test,
                n_repeats=self.n_repeats,
                random_state=42,
                n_jobs=-1,
            )
            importance_frames.append(pd.Series(result.importances_mean, index=feature_names))

        mean_importances = pd.concat(importance_frames, axis=1).fillna(0.0).mean(axis=1)
        results_df = mean_importances.rename("Importance").reset_index().rename(columns={"index": "Feature"})
        results_df = results_df.sort_values(by="Importance", ascending=False).head(10)

        self.latex_table = results_df.to_latex(
            index=False,
            caption="Top Secondary Predictors Isolating Demographics",
            label="tab:perm_imp",
        )

        self.plotly_figure = px.bar(
            results_df,
            x="Importance",
            y="Feature",
            orientation="h",
            title="Isolated Clinical Feature Importance (Excluding Demographics)",
        )
        self.plotly_figure.update_layout(yaxis={"categoryorder": "total ascending"})
