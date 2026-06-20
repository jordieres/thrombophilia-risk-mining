"""Clinical score screening experiment implementation.

This module trains the clinical score on the known binary criterion and then
applies the learned score card to records whose thrombophilia study is missing
or was not requested, producing a review-oriented ranking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from exp_clinical_risk_score import ClinicalRiskScoreExperiment, ModelEvaluation, StrategyResult


class ClinicalScoreScreeningExperiment(ClinicalRiskScoreExperiment):
    """Study 8: Apply the validated clinical score to unstudied or missing cases."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Clinical Score Screening"

    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        target_col: str = str(config.get("score_target_column", "ana_dura"))
        positive_label: str = str(config.get("score_positive_label", "Buscada positivo"))
        negative_label: str = str(config.get("score_negative_label", "Buscada negativo"))
        max_samples: int = int(config.get("score_max_samples", 4000))
        max_feature_cardinality: int = int(config.get("score_max_feature_cardinality", 12))
        numeric_bins: int = int(config.get("score_numeric_bins", 4))
        cv_splits: int = int(config.get("score_cv_splits", 5))
        top_features: int = int(config.get("score_top_features", 12))
        min_sensitivity: float = float(config.get("score_min_sensitivity", 0.90))
        min_feature_prevalence: float = float(config.get("score_min_feature_prevalence", 0.02))
        feature_strategy: str = str(config.get("score_feature_strategy", "compare"))
        benchmark_model: str = str(config.get("score_benchmark_model", "both"))
        xgboost_estimators: int = int(config.get("score_xgboost_estimators", 80))
        output_dir: Path = Path(str(config.get("output_dir", ".")))
        screening_labels_raw = config.get("screening_labels", ["Missing", "No buscada"])
        screening_labels: List[str] = [str(label) for label in screening_labels_raw]

        if feature_strategy not in {"automatic", "association", "compare"}:
            raise ValueError("score_feature_strategy must be one of: automatic, association, compare.")

        binary_df: pd.DataFrame = self._filter_binary_target(
            data=data,
            target_col=target_col,
            positive_label=positive_label,
            negative_label=negative_label,
            max_samples=max_samples,
        )
        identifier_col: str = "id_pacie" if "id_pacie" in binary_df.columns else "sample_index"
        if identifier_col == "sample_index":
            binary_df = binary_df.copy()
            binary_df[identifier_col] = np.arange(len(binary_df))

        screening_df: pd.DataFrame = self._filter_screening_rows(
            data=data,
            target_col=target_col,
            screening_labels=screening_labels,
            identifier_col=identifier_col,
        )

        y: np.ndarray = np.where(binary_df[target_col] == positive_label, 1, 0)
        effective_splits: int = self._resolve_cv_splits(y=y, requested_splits=cv_splits)
        cv = StratifiedKFold(n_splits=effective_splits, shuffle=True, random_state=42)

        results: List[StrategyResult] = []
        screening_exports: List[pd.DataFrame] = []
        benchmark_evaluations: List[ModelEvaluation] = []

        if feature_strategy in {"automatic", "compare"}:
            automatic_binary_df = self._prepare_automatic_modeling_frame(
                data=binary_df,
                target_col=target_col,
                positive_label=positive_label,
                negative_label=negative_label,
                max_samples=max_samples,
                max_feature_cardinality=max_feature_cardinality,
                numeric_bins=numeric_bins,
            )
            automatic_screen_df = self._prepare_automatic_screening_frame(
                data=screening_df,
                training_frame=automatic_binary_df,
                target_col=target_col,
                identifier_col=identifier_col,
                numeric_bins=numeric_bins,
            )
            automatic_result, automatic_screen_export = self._fit_screening_strategy(
                strategy_key="automatic",
                strategy_name="Automatic Integer Score",
                binary_df=automatic_binary_df,
                screening_df=automatic_screen_df,
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
            screening_exports.append(automatic_screen_export)

        if feature_strategy in {"association", "compare"}:
            association_binary_df = self._prepare_association_guided_frame(
                base_df=binary_df,
                target_col=target_col,
                identifier_col=identifier_col,
            )
            association_screen_df = self._prepare_association_guided_frame(
                base_df=screening_df,
                target_col=target_col,
                identifier_col=identifier_col,
            )
            association_result, association_screen_export = self._fit_screening_strategy(
                strategy_key="association_guided",
                strategy_name="Association-Guided Integer Score",
                binary_df=association_binary_df,
                screening_df=association_screen_df,
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
            screening_exports.append(association_screen_export)

        benchmark_binary_df = automatic_binary_df if feature_strategy in {"automatic", "compare"} else association_binary_df
        benchmark_screen_df = automatic_screen_df if feature_strategy in {"automatic", "compare"} else association_screen_df
        if benchmark_binary_df is not None and benchmark_screen_df is not None:
            benchmark_feature_df = benchmark_binary_df.drop(columns=[target_col, identifier_col])
            screening_feature_df = benchmark_screen_df.drop(columns=[target_col, identifier_col])
            if benchmark_model in {"logistic", "both"}:
                logistic_pipeline = self._build_logistic_pipeline(feature_cols=benchmark_feature_df.columns.tolist())
                logistic_eval = self._evaluate_probability_pipeline(
                    pipeline=logistic_pipeline,
                    X=benchmark_feature_df,
                    y=y,
                    cv=cv,
                    model_name="Logistic Probability Benchmark",
                    score_label="Predicted positive probability",
                    min_sensitivity=min_sensitivity,
                )
                benchmark_evaluations.append(logistic_eval)
                fitted_logistic = self._build_logistic_pipeline(feature_cols=benchmark_feature_df.columns.tolist())
                fitted_logistic.fit(benchmark_feature_df, y)
                screening_exports.append(
                    self._score_screening_with_probabilities(
                        prefix="logistic_benchmark",
                        pipeline=fitted_logistic,
                        X=screening_feature_df,
                        identifier_series=benchmark_screen_df[identifier_col],
                        outcome_series=benchmark_screen_df[target_col],
                        identifier_col=identifier_col,
                        target_col=target_col,
                        positive_label=positive_label,
                        evaluation=logistic_eval,
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
                xgb_eval = self._evaluate_probability_pipeline(
                    pipeline=xgb_pipeline,
                    X=benchmark_feature_df,
                    y=y,
                    cv=cv,
                    model_name="XGBoost Benchmark",
                    score_label="Predicted positive probability",
                    min_sensitivity=min_sensitivity,
                )
                benchmark_evaluations.append(xgb_eval)
                fitted_xgb = Pipeline(
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
                fitted_xgb.fit(benchmark_feature_df, y)
                screening_exports.append(
                    self._score_screening_with_probabilities(
                        prefix="xgboost_benchmark",
                        pipeline=fitted_xgb,
                        X=screening_feature_df,
                        identifier_series=benchmark_screen_df[identifier_col],
                        outcome_series=benchmark_screen_df[target_col],
                        identifier_col=identifier_col,
                        target_col=target_col,
                        positive_label=positive_label,
                        evaluation=xgb_eval,
                    )
                )

        if not results:
            raise ValueError("At least one screening score strategy must be available.")

        metrics_table: pd.DataFrame = self._build_metrics_table([result.evaluation for result in results] + benchmark_evaluations)
        screening_export_df: pd.DataFrame = self._merge_screening_exports(
            screening_exports=screening_exports,
            identifier_col=identifier_col,
            target_col=target_col,
        )
        screening_summary_df: pd.DataFrame = self._build_screening_summary(
            screening_export_df=screening_export_df,
            target_col=target_col,
            screening_labels=screening_labels,
        )
        self._export_screening_scores(screening_export_df=screening_export_df, output_dir=output_dir)

        self.latex_table = "\n\n".join(
            [
                metrics_table.to_latex(
                    index=False,
                    caption="Training ROC Performance Used for Screening Candidates",
                    label="tab:clinical_screening_roc",
                ),
                screening_summary_df.to_latex(
                    index=False,
                    caption="Counts of Positive Screening Flags Among Missing or Unrequested Studies",
                    label="tab:clinical_screening_summary",
                ),
            ]
        )
        self.plotly_figure = self._build_screening_figure(
            screening_export_df=screening_export_df,
            target_col=target_col,
        )

    def _filter_screening_rows(
        self,
        data: pd.DataFrame,
        target_col: str,
        screening_labels: List[str],
        identifier_col: str,
    ) -> pd.DataFrame:
        if target_col not in data.columns:
            raise ValueError(f"The clinical score screening experiment requires the target column '{target_col}'.")
        df = data.copy()
        df[target_col] = df[target_col].astype("string").fillna("Missing")
        df = df[df[target_col].isin(screening_labels)].reset_index(drop=True)
        if df.empty:
            raise ValueError("No rows matched the requested screening labels for the clinical score screening experiment.")
        if identifier_col not in df.columns:
            df[identifier_col] = np.arange(len(df))
        return df

    def _prepare_automatic_screening_frame(
        self,
        data: pd.DataFrame,
        training_frame: pd.DataFrame,
        target_col: str,
        identifier_col: str,
        numeric_bins: int,
    ) -> pd.DataFrame:
        training_feature_columns = [col for col in training_frame.columns if col not in {identifier_col, target_col}]
        rebuilt_features: Dict[str, pd.Series] = {}
        for column in data.columns:
            if column in {identifier_col, target_col}:
                continue
            if pd.api.types.is_numeric_dtype(data[column]):
                binned_series = self._bin_numeric_series(data[column], numeric_bins=numeric_bins)
                if binned_series is not None and column in training_feature_columns:
                    rebuilt_features[column] = binned_series
                continue
            if column in training_feature_columns:
                rebuilt_features[column] = data[column].astype("string").fillna("Missing").astype(str)

        base_df = data[[identifier_col, target_col]].copy()
        transformed_df = pd.DataFrame(index=data.index)
        for column in training_feature_columns:
            transformed_df[column] = rebuilt_features.get(column, pd.Series("Missing", index=data.index, dtype="object"))
        return pd.concat([base_df, transformed_df], axis=1).copy()

    def _fit_screening_strategy(
        self,
        strategy_key: str,
        strategy_name: str,
        binary_df: pd.DataFrame,
        screening_df: pd.DataFrame,
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
    ) -> tuple[StrategyResult, pd.DataFrame]:
        result = self._fit_and_evaluate_strategy(
            strategy_key=strategy_key,
            strategy_name=strategy_name,
            modeling_df=binary_df,
            identifier_col=identifier_col,
            target_col=target_col,
            positive_label=positive_label,
            negative_label=negative_label,
            cv=cv,
            top_features=top_features,
            min_sensitivity=min_sensitivity,
            coefficient_direction=coefficient_direction,
            positive_if_score_at_most=positive_if_score_at_most,
            min_feature_prevalence=min_feature_prevalence,
        )
        feature_df = binary_df.drop(columns=[target_col, identifier_col])
        fitted_pipeline = self._build_logistic_pipeline(feature_cols=feature_df.columns.tolist())
        fitted_pipeline.fit(feature_df, np.where(binary_df[target_col] == positive_label, 1, 0))
        points_table = self._build_points_table(
            pipeline=fitted_pipeline,
            top_features=top_features,
            model_label=strategy_name,
            coefficient_direction=coefficient_direction,
            X_reference=feature_df,
            min_feature_prevalence=min_feature_prevalence,
        )
        screening_scores = self._score_patients_with_points(
            strategy_key=strategy_key,
            pipeline=fitted_pipeline,
            X=screening_df.drop(columns=[target_col, identifier_col]),
            points_table=points_table,
            identifier_series=screening_df[identifier_col],
            outcome_series=screening_df[target_col],
            identifier_col=identifier_col,
            target_col=target_col,
            positive_label=positive_label,
            selected_threshold=result.evaluation.selected_threshold,
            positive_if_score_at_most=positive_if_score_at_most,
        )
        return result, screening_scores

    def _merge_screening_exports(
        self,
        screening_exports: List[pd.DataFrame],
        identifier_col: str,
        target_col: str,
    ) -> pd.DataFrame:
        merged = screening_exports[0]
        for export_df in screening_exports[1:]:
            merged = merged.merge(export_df, on=[identifier_col, target_col], how="outer")
        return merged

    def _build_screening_summary(
        self,
        screening_export_df: pd.DataFrame,
        target_col: str,
        screening_labels: List[str],
    ) -> pd.DataFrame:
        strategy_prefixes = sorted(
            {column.replace("_predicted_positive_at_rule_out_threshold", "") for column in screening_export_df.columns if column.endswith("_predicted_positive_at_rule_out_threshold")}
        )
        rows: List[Dict[str, Any]] = []
        for label in screening_labels:
            label_df = screening_export_df[screening_export_df[target_col] == label]
            row: Dict[str, Any] = {
                "Screening_Label": label,
                "N": int(len(label_df)),
            }
            for prefix in strategy_prefixes:
                flag_col = f"{prefix}_predicted_positive_at_rule_out_threshold"
                if flag_col in label_df.columns:
                    row[f"{prefix}_flagged_positive"] = int(label_df[flag_col].fillna(False).sum())
            rows.append(row)
        return pd.DataFrame(rows)

    def _build_screening_figure(
        self,
        screening_export_df: pd.DataFrame,
        target_col: str,
    ) -> go.Figure:
        figure = go.Figure()
        strategy_prefixes = sorted(
            {column.replace("_predicted_positive_at_rule_out_threshold", "") for column in screening_export_df.columns if column.endswith("_predicted_positive_at_rule_out_threshold")}
        )
        for prefix in strategy_prefixes:
            score_col = f"{prefix}_integer_score" if f"{prefix}_integer_score" in screening_export_df.columns else f"{prefix}_probability"
            if score_col not in screening_export_df.columns:
                continue
            for label in screening_export_df[target_col].dropna().astype(str).unique():
                label_df = screening_export_df[screening_export_df[target_col].astype(str) == label]
                figure.add_trace(
                    go.Histogram(
                        x=label_df[score_col],
                        name=f"{prefix}:{label}",
                        opacity=0.65,
                        histnorm="probability density",
                    )
                )
        figure.update_layout(
            title="Clinical Score Screening Distribution",
            barmode="overlay",
            xaxis_title="Clinical integer score",
            yaxis_title="Density",
        )
        return figure

    def _score_screening_with_probabilities(
        self,
        prefix: str,
        pipeline: Pipeline,
        X: pd.DataFrame,
        identifier_series: pd.Series,
        outcome_series: pd.Series,
        identifier_col: str,
        target_col: str,
        positive_label: str,
        evaluation: ModelEvaluation,
    ) -> pd.DataFrame:
        probabilities: np.ndarray = pipeline.predict_proba(X)[:, 1]
        threshold = evaluation.selected_threshold
        positive_flags = probabilities >= threshold
        return pd.DataFrame(
            {
                identifier_col: identifier_series.to_numpy(),
                target_col: outcome_series.to_numpy(),
                f"{prefix}_probability": probabilities,
                f"{prefix}_threshold_for_min_sensitivity": threshold,
                f"{prefix}_predicted_positive_at_rule_out_threshold": positive_flags,
                f"{prefix}_predicted_label_at_rule_out_threshold": np.where(
                    positive_flags,
                    positive_label,
                    f"not_{positive_label}",
                ),
            }
        )

    def _export_screening_scores(self, screening_export_df: pd.DataFrame, output_dir: Path) -> None:
        export_path: Path = output_dir / "clinical_risk_score_screening_candidates.csv"
        screening_export_df.to_csv(export_path, index=False)
