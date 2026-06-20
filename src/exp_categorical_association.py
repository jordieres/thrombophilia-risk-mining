"""Categorical association experiment implementation.

This module measures pairwise association strength across categorical clinical
variables using Cramer's V, exports the strongest relationships, and renders an
interactive heatmap for exploratory review.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
from scipy.stats import chi2_contingency

from experiment_base import BaseExperiment


class CategoricalAssociationExperiment(BaseExperiment):
    """Study 6: Pairwise association mapping across categorical variables."""

    def __init__(self) -> None:
        super().__init__("Categorical Association")

    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        """Builds a Cramer's V matrix and exports the strongest categorical pairs."""
        max_samples: int = int(config.get("association_max_samples", 5000))
        max_columns: int = int(config.get("association_max_columns", 20))
        top_k: int = int(config.get("association_top_k", 20))
        output_dir: Path = Path(str(config.get("output_dir", ".")))
        include_target: bool = bool(config.get("association_include_target", True))
        target_col: str = str(config.get("association_target_column", "ana_dura"))

        categorical_df: pd.DataFrame = data.select_dtypes(include=["object", "category"]).copy()
        categorical_df = categorical_df.drop(columns=["id_pacie"], errors="ignore")
        categorical_df = categorical_df.dropna(axis=1, how="all")

        if not include_target:
            categorical_df = categorical_df.drop(columns=[target_col], errors="ignore")

        if categorical_df.empty:
            raise ValueError("Categorical association requires at least one non-empty categorical feature.")

        profile_rows: List[Dict[str, Any]] = []
        for column in categorical_df.columns:
            profile_rows.append(
                {
                    "column": column,
                    "cardinality": int(categorical_df[column].nunique(dropna=False)),
                    "missing_rate": float(categorical_df[column].isna().mean()),
                }
            )

        profile_df: pd.DataFrame = pd.DataFrame(profile_rows)
        profile_df = profile_df.sort_values(by=["cardinality", "missing_rate", "column"]).reset_index(drop=True)
        selected_columns: List[str] = profile_df.head(max_columns)["column"].tolist()
        if target_col in categorical_df.columns and include_target and target_col not in selected_columns:
            selected_columns = [target_col] + selected_columns[:-1] if max_columns > 0 else [target_col]
            selected_columns = list(dict.fromkeys(selected_columns))

        selected_df: pd.DataFrame = categorical_df[selected_columns].copy()
        for column in selected_df.columns:
            selected_df[column] = selected_df[column].astype("object").where(selected_df[column].notna(), "Missing").astype(str)

        if len(selected_df) > max_samples:
            selected_df = selected_df.sample(n=max_samples, random_state=42).reset_index(drop=True)

        association_matrix: pd.DataFrame = self._build_cramers_v_matrix(selected_df)
        strongest_pairs_df: pd.DataFrame = self._build_top_pairs(association_matrix, top_k=top_k)

        matrix_output: Path = output_dir / "categorical_association_matrix.csv"
        pairs_output: Path = output_dir / "categorical_association_top_pairs.csv"
        association_matrix.to_csv(matrix_output, index=True)
        strongest_pairs_df.to_csv(pairs_output, index=False)

        self.latex_table = strongest_pairs_df.to_latex(
            index=False,
            caption="Strongest Pairwise Categorical Associations via Cramer's V",
            label="tab:categorical_association",
        )
        self.plotly_figure = px.imshow(
            association_matrix,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            zmin=0.0,
            zmax=1.0,
            aspect="auto",
            title="Categorical Association Heatmap (Cramer's V)",
        )
        self.plotly_figure.update_layout(
            xaxis_title="Variable",
            yaxis_title="Variable",
        )

    def _build_cramers_v_matrix(self, data: pd.DataFrame) -> pd.DataFrame:
        """Computes the symmetric pairwise Cramer's V matrix."""
        columns: List[str] = data.columns.tolist()
        matrix = pd.DataFrame(np.eye(len(columns)), index=columns, columns=columns, dtype=float)

        for left_index, left_column in enumerate(columns):
            for right_index in range(left_index + 1, len(columns)):
                right_column = columns[right_index]
                score = self._cramers_v(data[left_column], data[right_column])
                matrix.loc[left_column, right_column] = score
                matrix.loc[right_column, left_column] = score

        return matrix

    def _build_top_pairs(self, matrix: pd.DataFrame, top_k: int) -> pd.DataFrame:
        """Returns the strongest non-diagonal variable pairs in descending order."""
        rows: List[Dict[str, Any]] = []
        columns = matrix.columns.tolist()
        for left_index, left_column in enumerate(columns):
            for right_index in range(left_index + 1, len(columns)):
                right_column = columns[right_index]
                rows.append(
                    {
                        "variable_a": left_column,
                        "variable_b": right_column,
                        "cramers_v": float(matrix.loc[left_column, right_column]),
                    }
                )

        pairs_df = pd.DataFrame(rows)
        if pairs_df.empty:
            raise ValueError("Categorical association requires at least two categorical variables.")
        return pairs_df.sort_values(by=["cramers_v", "variable_a", "variable_b"], ascending=[False, True, True]).head(top_k).reset_index(drop=True)

    @staticmethod
    def _cramers_v(left: pd.Series, right: pd.Series) -> float:
        """Computes bias-reduced Cramer's V for two categorical series."""
        contingency_table = pd.crosstab(left, right)
        if contingency_table.empty:
            return 0.0

        chi2 = chi2_contingency(contingency_table, correction=False)[0]
        sample_size = contingency_table.to_numpy().sum()
        if sample_size == 0:
            return 0.0

        phi2 = chi2 / sample_size
        rows, cols = contingency_table.shape
        phi2_corrected = max(0.0, phi2 - ((cols - 1) * (rows - 1)) / max(sample_size - 1, 1))
        rows_corrected = rows - ((rows - 1) ** 2) / max(sample_size - 1, 1)
        cols_corrected = cols - ((cols - 1) ** 2) / max(sample_size - 1, 1)
        denominator = min(rows_corrected - 1, cols_corrected - 1)
        if denominator <= 0:
            return 0.0
        return float(np.sqrt(phi2_corrected / denominator))
