"""Clinical risk-score experiment implementation.

This module supports two feature-selection strategies for a bedside-oriented
clinical score:

* an automatic low-cardinality discovery workflow,
* an association-guided preset derived from the rule-mining findings.

Both strategies can be benchmarked with ROC curves and exported at the patient
level for direct comparison.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import sparse
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

from experiment_base import BaseExperiment


@dataclass(frozen=True)
class ModelEvaluation:
    """Container for out-of-fold predictions and ROC metrics."""

    model_name: str
    score_label: str
    y_true: np.ndarray
    scores: np.ndarray
    probabilities: np.ndarray
    auc: float
    fpr: np.ndarray
    tpr: np.ndarray
    thresholds: np.ndarray
    selected_threshold: float
    sensitivity: float
    specificity: float
    threshold_method: str
    positive_if_score_at_most: bool


@dataclass(frozen=True)
class StrategyResult:
    """Stores the outputs of one clinical-score strategy."""

    strategy_key: str
    strategy_name: str
    evaluation: ModelEvaluation
    points_table: pd.DataFrame
    patient_scores_df: pd.DataFrame
    score_summary: pd.DataFrame


class ClinicalRiskScoreExperiment(BaseExperiment):
    """Study 5: Clinically interpretable integer-point risk score with ROC benchmarking."""

    ASSOCIATION_GUIDED_COMPONENTS: Sequence[str] = (
        "female_sex_rule",
        "age_lt50_rule",
        "age_50_69_rule",
        "no_prior_dvt_rule",
        "normal_hemoglobin_rule",
        "negative_ddimer_rule",
        "no_malignancy_rule",
        "no_immobilization_rule",
    )

    def __init__(self) -> None:
        super().__init__("Clinical Risk Score")

    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        """Builds one or more integer-point clinical scores and evaluates ROC performance."""
        target_col: str = str(config.get("score_target_column", "ana_dura"))
        positive_label: str = str(config.get("score_positive_label", "Buscada positivo"))
        negative_label: str = str(config.get("score_negative_label", "Buscada negativo"))
        max_samples: int = int(config.get("score_max_samples", 4000))
        max_feature_cardinality: int = int(config.get("score_max_feature_cardinality", 12))
        numeric_bins: int = int(config.get("score_numeric_bins", 4))
        cv_splits: int = int(config.get("score_cv_splits", 5))
        benchmark_model: str = str(config.get("score_benchmark_model", "both"))
        top_features: int = int(config.get("score_top_features", 12))
        min_sensitivity: float = float(config.get("score_min_sensitivity", 0.90))
        min_feature_prevalence: float = float(config.get("score_min_feature_prevalence", 0.02))
        xgboost_estimators: int = int(config.get("score_xgboost_estimators", 80))
        feature_strategy: str = str(config.get("score_feature_strategy", "automatic"))
        output_dir: Path = Path(str(config.get("output_dir", ".")))

        if feature_strategy not in {"automatic", "association", "compare"}:
            raise ValueError("score_feature_strategy must be one of: automatic, association, compare.")

        filtered_source_df: pd.DataFrame = self._filter_binary_target(
            data=data,
            target_col=target_col,
            positive_label=positive_label,
            negative_label=negative_label,
            max_samples=max_samples,
        )
        identifier_col: str = "id_pacie" if "id_pacie" in filtered_source_df.columns else "sample_index"
        if identifier_col == "sample_index":
            filtered_source_df = filtered_source_df.copy()
            filtered_source_df[identifier_col] = np.arange(len(filtered_source_df))

        automatic_df: pd.DataFrame = self._prepare_automatic_modeling_frame(
            data=filtered_source_df,
            target_col=target_col,
            positive_label=positive_label,
            negative_label=negative_label,
            max_samples=max_samples,
            max_feature_cardinality=max_feature_cardinality,
            numeric_bins=numeric_bins,
        )
        association_df: pd.DataFrame = self._prepare_association_guided_frame(
            base_df=filtered_source_df,
            target_col=target_col,
            identifier_col=identifier_col,
        )

        y: np.ndarray = np.where(filtered_source_df[target_col] == positive_label, 1, 0)
        effective_splits: int = self._resolve_cv_splits(y=y, requested_splits=cv_splits)
        cv = StratifiedKFold(n_splits=effective_splits, shuffle=True, random_state=42)

        results: List[StrategyResult] = []
        if feature_strategy in {"automatic", "compare"}:
            automatic_result = self._fit_and_evaluate_strategy(
                strategy_key="automatic",
                strategy_name="Automatic Integer Score",
                modeling_df=automatic_df,
                identifier_col=identifier_col,
                target_col=target_col,
                positive_label=positive_label,
                negative_label=negative_label,
                cv=cv,
                top_features=top_features,
                min_sensitivity=min_sensitivity,
                coefficient_direction="positive",
                positive_if_score_at_most=False,
                min_feature_prevalence=min_feature_prevalence,
            )
            results.append(automatic_result)
        else:
            automatic_result = None

        if feature_strategy in {"association", "compare"}:
            association_result = self._fit_and_evaluate_strategy(
                strategy_key="association_guided",
                strategy_name="Association-Guided Integer Score",
                modeling_df=association_df,
                identifier_col=identifier_col,
                target_col=target_col,
                positive_label=positive_label,
                negative_label=negative_label,
                cv=cv,
                top_features=top_features,
                min_sensitivity=min_sensitivity,
                coefficient_direction="negative",
                positive_if_score_at_most=True,
                min_feature_prevalence=min_feature_prevalence,
            )
            results.append(association_result)
        else:
            association_result = None

        evaluations: List[ModelEvaluation] = [result.evaluation for result in results]

        benchmark_source_df: pd.DataFrame = automatic_df if automatic_result is not None else association_df
        benchmark_feature_df: pd.DataFrame = benchmark_source_df.drop(columns=[target_col, identifier_col])
        benchmark_pipeline = self._build_logistic_pipeline(feature_cols=benchmark_feature_df.columns.tolist())

        if benchmark_model in {"logistic", "both"}:
            evaluations.append(
                self._evaluate_probability_pipeline(
                    pipeline=benchmark_pipeline,
                    X=benchmark_feature_df,
                    y=y,
                    cv=cv,
                    model_name="Logistic Probability Benchmark",
                    score_label="Predicted positive probability",
                    min_sensitivity=min_sensitivity,
                )
            )

        if benchmark_model in {"xgboost", "both"}:
            xgb_pipeline = Pipeline(
                steps=[
                    ("preprocessor", self._build_preprocessor(feature_cols=benchmark_feature_df.columns.tolist())),
                    (
                        "model",
                        XGBClassifier(
                            n_estimators=xgboost_estimators,
                            max_depth=3,
                            learning_rate=0.08,
                            subsample=0.8,
                            colsample_bytree=0.8,
                            eval_metric="logloss",
                            random_state=42,
                            n_jobs=1,
                        ),
                    ),
                ]
            )
            evaluations.append(
                self._evaluate_probability_pipeline(
                    pipeline=xgb_pipeline,
                    X=benchmark_feature_df,
                    y=y,
                    cv=cv,
                    model_name="XGBoost Benchmark",
                    score_label="Predicted positive probability",
                    min_sensitivity=min_sensitivity,
                )
            )

        metrics_table: pd.DataFrame = self._build_metrics_table(evaluations=evaluations)
        combined_score_summary: pd.DataFrame = pd.concat(
            [result.score_summary for result in results],
            ignore_index=True,
        )
        combined_points_table: pd.DataFrame = pd.concat(
            [result.points_table for result in results],
            ignore_index=True,
        )
        export_df: pd.DataFrame = self._merge_patient_score_exports(
            automatic_result=automatic_result,
            association_result=association_result,
            identifier_col=identifier_col,
            target_col=target_col,
        )
        self._export_patient_scores(patient_scores_df=export_df, output_dir=output_dir)

        self.latex_table = "\n\n".join(
            [
                metrics_table.to_latex(
                    index=False,
                    caption="Cross-Validated ROC Performance for the Clinical Criterion",
                    label="tab:clinical_roc",
                ),
                combined_score_summary.to_latex(
                    index=False,
                    caption="Clinical Integer-Score Distribution by Diagnostic Outcome",
                    label="tab:clinical_score_distribution",
                ),
                combined_points_table.to_latex(
                    index=False,
                    caption="Integer Point Components of the Clinical Risk Score Strategies",
                    label="tab:clinical_score_components",
                ),
            ]
        )
        primary_result: StrategyResult = results[0]
        self.plotly_figure = self._build_roc_figure(
            evaluations=evaluations,
            clinical_eval=primary_result.evaluation,
            positive_label=positive_label,
            negative_label=negative_label,
        )

    def _fit_and_evaluate_strategy(
        self,
        strategy_key: str,
        strategy_name: str,
        modeling_df: pd.DataFrame,
        identifier_col: str,
        target_col: str,
        positive_label: str,
        negative_label: str,
        cv: StratifiedKFold,
        top_features: int,
        min_sensitivity: float,
        coefficient_direction: str,
        positive_if_score_at_most: bool,
        min_feature_prevalence: float,
    ) -> StrategyResult:
        """Fits one score strategy end to end."""
        y: np.ndarray = np.where(modeling_df[target_col] == positive_label, 1, 0)
        feature_df: pd.DataFrame = modeling_df.drop(columns=[target_col, identifier_col])
        pipeline = self._build_logistic_pipeline(feature_cols=feature_df.columns.tolist())

        evaluation: ModelEvaluation = self._evaluate_clinical_score_pipeline(
            pipeline=pipeline,
            X=feature_df,
            y=y,
            cv=cv,
            top_features=top_features,
            min_sensitivity=min_sensitivity,
            model_name=strategy_name,
            coefficient_direction=coefficient_direction,
            positive_if_score_at_most=positive_if_score_at_most,
            min_feature_prevalence=min_feature_prevalence,
        )

        fitted_pipeline = clone(pipeline)
        fitted_pipeline.fit(feature_df, y)
        points_table: pd.DataFrame = self._build_points_table(
            pipeline=fitted_pipeline,
            top_features=top_features,
            model_label=strategy_name,
            coefficient_direction=coefficient_direction,
            X_reference=feature_df,
            min_feature_prevalence=min_feature_prevalence,
        )
        patient_scores_df: pd.DataFrame = self._score_patients_with_points(
            strategy_key=strategy_key,
            pipeline=fitted_pipeline,
            X=feature_df,
            points_table=points_table,
            identifier_series=modeling_df[identifier_col],
            outcome_series=modeling_df[target_col],
            identifier_col=identifier_col,
            target_col=target_col,
            positive_label=positive_label,
            selected_threshold=evaluation.selected_threshold,
            positive_if_score_at_most=evaluation.positive_if_score_at_most,
        )
        score_summary: pd.DataFrame = self._build_score_summary(
            scores=evaluation.scores,
            y_true=evaluation.y_true,
            positive_label=positive_label,
            negative_label=negative_label,
            model_name=strategy_name,
        )
        return StrategyResult(
            strategy_key=strategy_key,
            strategy_name=strategy_name,
            evaluation=evaluation,
            points_table=points_table,
            patient_scores_df=patient_scores_df,
            score_summary=score_summary,
        )

    def _prepare_automatic_modeling_frame(
        self,
        data: pd.DataFrame,
        target_col: str,
        positive_label: str,
        negative_label: str,
        max_samples: int,
        max_feature_cardinality: int,
        numeric_bins: int,
    ) -> pd.DataFrame:
        """Builds the existing automatic low-cardinality feature set."""
        df: pd.DataFrame = self._filter_binary_target(
            data=data,
            target_col=target_col,
            positive_label=positive_label,
            negative_label=negative_label,
            max_samples=max_samples,
        )

        selected_columns: List[str] = [target_col]
        if "id_pacie" in df.columns:
            selected_columns.insert(0, "id_pacie")

        transformed_features: Dict[str, pd.Series] = {}
        for column in df.columns:
            if column in {target_col, "id_pacie"}:
                continue
            if pd.api.types.is_numeric_dtype(df[column]):
                binned_series = self._bin_numeric_series(df[column], numeric_bins=numeric_bins)
                if binned_series is not None:
                    transformed_features[column] = binned_series
                continue
            unique_count: int = int(df[column].nunique(dropna=False))
            if 2 <= unique_count <= max_feature_cardinality:
                transformed_features[column] = df[column].astype("string").fillna("Missing").astype(str)

        if not transformed_features:
            raise ValueError(
                "No eligible features remained for the clinical score model. "
                "Increase --score-max-feature-cardinality or review the dataset schema."
            )

        base_df: pd.DataFrame = df[selected_columns].copy()
        transformed_df: pd.DataFrame = pd.DataFrame(transformed_features, index=df.index)
        return pd.concat([base_df, transformed_df], axis=1).copy()

    def _prepare_association_guided_frame(
        self,
        base_df: pd.DataFrame,
        target_col: str,
        identifier_col: str,
    ) -> pd.DataFrame:
        """Builds a fixed binary score card driven by the association-rule findings."""
        guided_df = base_df[[identifier_col, target_col]].copy()

        if "sexo" in base_df.columns:
            sex_values = base_df["sexo"].astype(str)
            guided_df["female_sex_rule"] = np.where(sex_values.isin(["Female", "Mujer"]), "Yes", "No")

        if "edad" in base_df.columns:
            age_values = pd.to_numeric(base_df["edad"], errors="coerce")
            guided_df["age_lt50_rule"] = np.where((age_values < 50).fillna(False), "Yes", "No")
            guided_df["age_50_69_rule"] = np.where(((age_values >= 50) & (age_values <= 69)).fillna(False), "Yes", "No")

        if "fr_tvp_p" in base_df.columns:
            prior_dvt_values = pd.to_numeric(base_df["fr_tvp_p"], errors="coerce")
            guided_df["no_prior_dvt_rule"] = np.where(prior_dvt_values.fillna(0) <= 0, "Yes", "No")
        elif "fr_tvp_a" in base_df.columns:
            guided_df["no_prior_dvt_rule"] = np.where(base_df["fr_tvp_a"].astype(str) == "No", "Yes", "No")

        if "ana_hemo" in base_df.columns:
            hemo_values = pd.to_numeric(base_df["ana_hemo"], errors="coerce")
            guided_df["normal_hemoglobin_rule"] = np.where((hemo_values >= 12.0).fillna(False), "Yes", "No")

        if "ddvalmcg" in base_df.columns:
            ddimer_values = pd.to_numeric(base_df["ddvalmcg"], errors="coerce")
            guided_df["negative_ddimer_rule"] = np.where((ddimer_values <= 0.5).fillna(False), "Yes", "No")
        elif "ana_dime" in base_df.columns:
            guided_df["negative_ddimer_rule"] = np.where(base_df["ana_dime"].astype(str) == "Negativo", "Yes", "No")

        if "fr_cance" in base_df.columns:
            guided_df["no_malignancy_rule"] = np.where(base_df["fr_cance"].astype(str) == "No", "Yes", "No")

        if "fr_inmov" in base_df.columns:
            guided_df["no_immobilization_rule"] = np.where(base_df["fr_inmov"].astype(str) == "No", "Yes", "No")

        feature_cols = [col for col in self.ASSOCIATION_GUIDED_COMPONENTS if col in guided_df.columns]
        if not feature_cols:
            raise ValueError("No association-guided components could be mapped from the current dataset schema.")
        return guided_df[[identifier_col, target_col] + feature_cols].copy()

    def _filter_binary_target(
        self,
        data: pd.DataFrame,
        target_col: str,
        positive_label: str,
        negative_label: str,
        max_samples: int,
    ) -> pd.DataFrame:
        """Restricts the cohort to the binary criterion and stratified sample cap."""
        if target_col not in data.columns:
            raise ValueError(f"The clinical score experiment requires the target column '{target_col}'.")
        df: pd.DataFrame = data.copy()
        df[target_col] = df[target_col].astype("string")
        df = df[df[target_col].isin([positive_label, negative_label])].reset_index(drop=True)
        if df.empty:
            raise ValueError("No rows matched the requested positive/negative labels for the clinical score experiment.")
        if len(df) > max_samples:
            total_rows: int = len(df)
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
        return df

    def _bin_numeric_series(self, series: pd.Series, numeric_bins: int) -> pd.Series | None:
        """Converts a numeric feature into quantile bins suitable for point scoring."""
        non_null = series.dropna()
        if non_null.nunique() < 2:
            return None
        effective_bins: int = min(numeric_bins, int(non_null.nunique()))
        if effective_bins < 2:
            return None
        try:
            binned = pd.qcut(non_null, q=effective_bins, duplicates="drop")
        except ValueError:
            return None
        if getattr(binned, "cat", None) is None or len(binned.cat.categories) < 2:
            return None
        labels = binned.astype(str)
        full_series = pd.Series(index=series.index, dtype="object")
        full_series.loc[labels.index] = labels.to_numpy()
        full_series = full_series.fillna("Missing")
        return full_series.astype(str)

    def _build_logistic_pipeline(self, feature_cols: Sequence[str]) -> Pipeline:
        """Creates the logistic score pipeline for a given feature set."""
        return Pipeline(
            steps=[
                ("preprocessor", self._build_preprocessor(feature_cols=feature_cols)),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1000,
                        solver="liblinear",
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        )

    def _build_preprocessor(self, feature_cols: Sequence[str]) -> ColumnTransformer:
        """Creates a one-hot preprocessing graph for bedside-friendly point scoring."""
        return ColumnTransformer(
            transformers=[
                (
                    "cat",
                    Pipeline(
                        steps=[
                            ("imputer", SimpleImputer(strategy="constant", fill_value="Missing")),
                            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=True, drop="if_binary")),
                        ]
                    ),
                    list(feature_cols),
                )
            ]
        )

    def _resolve_cv_splits(self, y: np.ndarray, requested_splits: int) -> int:
        """Caps the CV fold count by the smallest class size."""
        class_counts = np.bincount(y)
        smallest_class: int = int(class_counts.min()) if len(class_counts) > 1 else 0
        effective_splits: int = min(requested_splits, smallest_class)
        if effective_splits < 2:
            raise ValueError("At least two samples per class are required to compute cross-validated ROC curves.")
        return effective_splits

    def _evaluate_clinical_score_pipeline(
        self,
        pipeline: Pipeline,
        X: pd.DataFrame,
        y: np.ndarray,
        cv: StratifiedKFold,
        top_features: int,
        min_sensitivity: float,
        model_name: str,
        coefficient_direction: str,
        positive_if_score_at_most: bool,
        min_feature_prevalence: float,
    ) -> ModelEvaluation:
        """Evaluates one integer-point clinical score with out-of-fold predictions."""
        point_scores: np.ndarray = np.zeros(len(X), dtype=float)
        probabilities: np.ndarray = np.zeros(len(X), dtype=float)
        for train_idx, test_idx in cv.split(X, y):
            fold_pipeline = clone(pipeline)
            fold_pipeline.fit(X.iloc[train_idx], y[train_idx])
            fold_points_table = self._build_points_table(
                fold_pipeline,
                top_features=top_features,
                model_label=model_name,
                coefficient_direction=coefficient_direction,
                X_reference=X.iloc[train_idx],
                min_feature_prevalence=min_feature_prevalence,
            )
            point_scores[test_idx] = self._score_feature_frame_with_points(
                pipeline=fold_pipeline,
                X=X.iloc[test_idx],
                points_table=fold_points_table,
            )
            probabilities[test_idx] = fold_pipeline.predict_proba(X.iloc[test_idx])[:, 1]
        return self._build_evaluation(
            model_name=model_name,
            score_label="Integer point score",
            y_true=y,
            scores=point_scores,
            probabilities=probabilities,
            min_sensitivity=min_sensitivity,
            positive_if_score_at_most=positive_if_score_at_most,
        )

    def _evaluate_probability_pipeline(
        self,
        pipeline: Pipeline,
        X: pd.DataFrame,
        y: np.ndarray,
        cv: StratifiedKFold,
        model_name: str,
        score_label: str,
        min_sensitivity: float,
    ) -> ModelEvaluation:
        """Evaluates a probability-based classifier with out-of-fold scores."""
        probabilities: np.ndarray = np.zeros(len(X), dtype=float)
        for train_idx, test_idx in cv.split(X, y):
            fold_pipeline = clone(pipeline)
            fold_pipeline.fit(X.iloc[train_idx], y[train_idx])
            probabilities[test_idx] = fold_pipeline.predict_proba(X.iloc[test_idx])[:, 1]
        return self._build_evaluation(
            model_name=model_name,
            score_label=score_label,
            y_true=y,
            scores=probabilities,
            probabilities=probabilities,
            min_sensitivity=min_sensitivity,
        )

    def _build_points_table(
        self,
        pipeline: Pipeline,
        top_features: int,
        model_label: str,
        coefficient_direction: str,
        X_reference: pd.DataFrame,
        min_feature_prevalence: float,
    ) -> pd.DataFrame:
        """Extracts score components and converts them to integer points."""
        preprocessor: ColumnTransformer = pipeline.named_steps["preprocessor"]
        model: LogisticRegression = pipeline.named_steps["model"]
        feature_names: np.ndarray = preprocessor.get_feature_names_out()
        coefficients: np.ndarray = model.coef_.ravel()
        transformed = preprocessor.transform(X_reference)
        transformed_sparse = transformed if sparse.issparse(transformed) else sparse.csr_matrix(transformed)
        prevalence = np.asarray(transformed_sparse.mean(axis=0)).ravel()
        coef_df: pd.DataFrame = pd.DataFrame(
            {
                "Encoded_Feature": feature_names,
                "Coefficient": coefficients,
                "Odds_Ratio": np.exp(coefficients),
                "Prevalence": prevalence,
            }
        )
        coef_df["Component"] = coef_df["Encoded_Feature"].str.replace("cat__", "", regex=False)
        coef_df = coef_df[~coef_df["Component"].str.endswith("_Missing")].copy()
        coef_df = coef_df[coef_df["Prevalence"] >= min_feature_prevalence].copy()
        if coefficient_direction == "positive":
            coef_df = coef_df[coef_df["Coefficient"] > 0].copy()
        else:
            coef_df = coef_df[coef_df["Coefficient"] < 0].copy()
            coef_df["Coefficient_Abs"] = coef_df["Coefficient"].abs()
        if coef_df.empty:
            raise ValueError(
                "The fitted logistic model produced no eligible coefficients after prevalence and missing-value filtering."
            )
        sort_col = "Coefficient" if coefficient_direction == "positive" else "Coefficient_Abs"
        coef_df = coef_df.sort_values(by=[sort_col, "Prevalence"], ascending=[False, False]).head(top_features).reset_index(drop=True)
        base_coef: float = float(coef_df[sort_col].min())
        coef_df["Points"] = np.maximum(1, np.rint(coef_df[sort_col] / base_coef)).astype(int)
        coef_df["Model"] = model_label
        drop_cols = [col for col in ["Coefficient_Abs", "Prevalence"] if col in coef_df.columns]
        coef_df = coef_df.drop(columns=drop_cols)
        return coef_df[["Model", "Component", "Coefficient", "Odds_Ratio", "Points"]]

    def _score_feature_frame_with_points(
        self,
        pipeline: Pipeline,
        X: pd.DataFrame,
        points_table: pd.DataFrame,
    ) -> np.ndarray:
        """Applies the point card to an arbitrary feature frame."""
        preprocessor: ColumnTransformer = pipeline.named_steps["preprocessor"]
        transformed = preprocessor.transform(X)
        transformed_sparse = transformed if sparse.issparse(transformed) else sparse.csr_matrix(transformed)
        feature_names: List[str] = list(preprocessor.get_feature_names_out())
        selected_features: List[str] = [f"cat__{component}" for component in points_table["Component"].tolist()]
        selected_indices: List[int] = [feature_names.index(feature) for feature in selected_features if feature in feature_names]
        selected_points: np.ndarray = points_table["Points"].to_numpy(dtype=float)
        if not selected_indices:
            return np.zeros(X.shape[0], dtype=float)
        return np.asarray(transformed_sparse[:, selected_indices] @ selected_points).ravel()

    def _score_patients_with_points(
        self,
        strategy_key: str,
        pipeline: Pipeline,
        X: pd.DataFrame,
        points_table: pd.DataFrame,
        identifier_series: pd.Series,
        outcome_series: pd.Series,
        identifier_col: str,
        target_col: str,
        positive_label: str,
        selected_threshold: float,
        positive_if_score_at_most: bool,
    ) -> pd.DataFrame:
        """Builds the patient-level exported score table using the final fitted score card."""
        point_scores: np.ndarray = self._score_feature_frame_with_points(pipeline=pipeline, X=X, points_table=points_table)
        probabilities: np.ndarray = pipeline.predict_proba(X)[:, 1]
        prefix = strategy_key
        return pd.DataFrame(
            {
                identifier_col: identifier_series.to_numpy(),
                target_col: outcome_series.to_numpy(),
                f"{prefix}_integer_score": point_scores,
                f"{prefix}_logistic_probability": probabilities,
                f"{prefix}_threshold_for_min_sensitivity": selected_threshold,
                f"{prefix}_predicted_positive_at_rule_out_threshold": (point_scores <= selected_threshold) if positive_if_score_at_most else (point_scores >= selected_threshold),
                f"{prefix}_predicted_label_at_rule_out_threshold": np.where(
                    (point_scores <= selected_threshold) if positive_if_score_at_most else (point_scores >= selected_threshold),
                    positive_label,
                    f"not_{positive_label}",
                ),
            }
        )

    def _build_evaluation(
        self,
        model_name: str,
        score_label: str,
        y_true: np.ndarray,
        scores: np.ndarray,
        probabilities: np.ndarray,
        min_sensitivity: float,
        positive_if_score_at_most: bool = False,
    ) -> ModelEvaluation:
        """Computes ROC metrics and selects the operating threshold under a sensitivity constraint."""
        effective_scores = -scores if positive_if_score_at_most else scores
        fpr, tpr, thresholds = roc_curve(y_true, effective_scores)
        auc: float = float(roc_auc_score(y_true, effective_scores))
        selected_idx: int = self._select_threshold_idx(
            tpr=tpr,
            fpr=fpr,
            thresholds=thresholds,
            min_sensitivity=min_sensitivity,
        )
        return ModelEvaluation(
            model_name=model_name,
            score_label=score_label,
            y_true=y_true,
            scores=scores,
            probabilities=probabilities,
            auc=auc,
            fpr=fpr,
            tpr=tpr,
            thresholds=thresholds,
            selected_threshold=float(-thresholds[selected_idx] if positive_if_score_at_most else thresholds[selected_idx]),
            sensitivity=float(tpr[selected_idx]),
            specificity=float(1.0 - fpr[selected_idx]),
            threshold_method=f"Sensitivity >= {min_sensitivity:.2f}",
            positive_if_score_at_most=positive_if_score_at_most,
        )

    def _select_threshold_idx(
        self,
        tpr: np.ndarray,
        fpr: np.ndarray,
        thresholds: np.ndarray,
        min_sensitivity: float,
    ) -> int:
        """Chooses the most specific threshold that still meets the sensitivity target."""
        eligible = np.where(tpr >= min_sensitivity)[0]
        if len(eligible) == 0:
            return int(np.argmax(tpr))
        eligible_specificity = 1.0 - fpr[eligible]
        best_specificity: float = float(np.max(eligible_specificity))
        specificity_best = eligible[np.where(np.isclose(eligible_specificity, best_specificity))[0]]
        return int(specificity_best[np.argmax(thresholds[specificity_best])])

    def _build_metrics_table(self, evaluations: Sequence[ModelEvaluation]) -> pd.DataFrame:
        """Creates a concise ROC operating summary."""
        return pd.DataFrame(
            [
                {
                    "Model": evaluation.model_name,
                    "AUC": evaluation.auc,
                    "Threshold_Method": evaluation.threshold_method,
                    "Selected_Threshold": evaluation.selected_threshold,
                    "Decision_Rule": "score <= threshold" if evaluation.positive_if_score_at_most else "score >= threshold",
                    "Sensitivity": evaluation.sensitivity,
                    "Specificity": evaluation.specificity,
                }
                for evaluation in evaluations
            ]
        )

    def _build_score_summary(
        self,
        scores: np.ndarray,
        y_true: np.ndarray,
        positive_label: str,
        negative_label: str,
        model_name: str,
    ) -> pd.DataFrame:
        """Summarizes the integer clinical score per outcome class."""
        rows: List[Dict[str, Any]] = []
        for class_value, label in [(0, negative_label), (1, positive_label)]:
            class_scores = scores[y_true == class_value]
            rows.append(
                {
                    "Model": model_name,
                    "Outcome": label,
                    "N": int(len(class_scores)),
                    "Mean_Score": float(np.mean(class_scores)),
                    "Median_Score": float(np.median(class_scores)),
                    "Std_Score": float(np.std(class_scores)),
                    "P25_Score": float(np.quantile(class_scores, 0.25)),
                    "P75_Score": float(np.quantile(class_scores, 0.75)),
                }
            )
        return pd.DataFrame(rows)

    def _merge_patient_score_exports(
        self,
        automatic_result: StrategyResult | None,
        association_result: StrategyResult | None,
        identifier_col: str,
        target_col: str,
    ) -> pd.DataFrame:
        """Merges patient-level exports from the selected strategies."""
        exports: List[pd.DataFrame] = []
        if automatic_result is not None:
            exports.append(automatic_result.patient_scores_df)
        if association_result is not None:
            exports.append(association_result.patient_scores_df)
        if not exports:
            raise ValueError("At least one patient-level score export must be available.")
        merged = exports[0]
        for export_df in exports[1:]:
            merged = merged.merge(export_df, on=[identifier_col, target_col], how="outer")
        return merged

    def _build_roc_figure(
        self,
        evaluations: Sequence[ModelEvaluation],
        clinical_eval: ModelEvaluation,
        positive_label: str,
        negative_label: str,
    ) -> go.Figure:
        """Builds a combined ROC and clinical-score distribution figure."""
        figure = make_subplots(rows=1, cols=2, subplot_titles=("ROC Curves", "Clinical Score Distribution"))
        for evaluation in evaluations:
            figure.add_trace(
                go.Scatter(
                    x=evaluation.fpr,
                    y=evaluation.tpr,
                    mode="lines",
                    name=f"{evaluation.model_name} (AUC={evaluation.auc:.3f})",
                    hovertemplate=(
                        "Model: " + evaluation.model_name + "<br>"
                        "False Positive Rate: %{x:.3f}<br>"
                        "True Positive Rate: %{y:.3f}<extra></extra>"
                    ),
                ),
                row=1,
                col=1,
            )
        figure.add_trace(
            go.Scatter(
                x=[0.0, 1.0],
                y=[0.0, 1.0],
                mode="lines",
                name="Random baseline",
                line=dict(dash="dash", color="gray"),
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )
        negative_scores = clinical_eval.scores[clinical_eval.y_true == 0]
        positive_scores = clinical_eval.scores[clinical_eval.y_true == 1]
        figure.add_trace(
            go.Histogram(
                x=negative_scores,
                nbinsx=30,
                name=f"{negative_label} score",
                opacity=0.65,
                histnorm="probability density",
            ),
            row=1,
            col=2,
        )
        figure.add_trace(
            go.Histogram(
                x=positive_scores,
                nbinsx=30,
                name=f"{positive_label} score",
                opacity=0.65,
                histnorm="probability density",
            ),
            row=1,
            col=2,
        )
        figure.add_vline(
            x=clinical_eval.selected_threshold,
            line_dash="dot",
            line_color="black",
            annotation_text=f"Sensitivity-safe threshold={clinical_eval.selected_threshold:.0f}",
            row=1,
            col=2,
        )
        figure.update_xaxes(title_text="False Positive Rate", row=1, col=1)
        figure.update_yaxes(title_text="True Positive Rate", row=1, col=1)
        figure.update_xaxes(title_text="Clinical integer score", row=1, col=2)
        figure.update_yaxes(title_text="Density", row=1, col=2)
        figure.update_layout(title="Clinical Integer Risk Score ROC Benchmark", barmode="overlay", legend_title="Criterion")
        return figure

    def _export_patient_scores(self, patient_scores_df: pd.DataFrame, output_dir: Path) -> None:
        """Writes a patient-level clinical score file for downstream review."""
        export_path: Path = output_dir / "clinical_risk_score_per_patient.csv"
        patient_scores_df.to_csv(export_path, index=False)
