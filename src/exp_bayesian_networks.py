"""Bayesian-style aggregation experiment.

This module builds a simple conditional probability table for a chosen target
outcome grouped by a configurable categorical parent variable. It does not
require a full graphical-model dependency to generate the exported summary.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import plotly.express as px

from experiment_base import BaseExperiment


class BayesianNetworkExperiment(BaseExperiment):
    """Study 4: Joint probability modeling and causal gatekeeping parameter estimations."""

    def __init__(self) -> None:
        super().__init__("Bayesian Network Probabilistic Modeling")

    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        """Models conditional probability distribution charts to isolate wasted testing indices."""
        df: pd.DataFrame = data.copy()
        target_col: str = str(config.get("bayesian_target_column", "ana_dura"))
        group_col: str = str(config.get("bayesian_group_column", "sexo"))
        valid_target_labels = [str(label) for label in config.get("bayesian_target_valid_labels", [])]

        if target_col not in df.columns:
            raise ValueError(f"Bayesian summary requires the target column '{target_col}'.")
        if group_col not in df.columns:
            df[group_col] = "Missing"

        if valid_target_labels:
            df[target_col] = df[target_col].astype("string")
            df = df[df[target_col].isin(valid_target_labels)].reset_index(drop=True)
            if df.empty:
                raise ValueError(f"No rows matched bayesian_target_valid_labels for target column '{target_col}'.")

        if group_col == "sexo":
            df[group_col] = df[group_col].replace({"Male": "Hombre", "Female": "Mujer"})

        df[group_col] = df[group_col].astype("string").fillna("Missing")
        df[target_col] = df[target_col].astype("string").fillna("Missing")

        cpt: pd.DataFrame = pd.crosstab(
            index=[df[group_col]],
            columns=df[target_col],
            normalize="index",
        ).reset_index()

        self.latex_table = cpt.to_latex(
            index=False,
            caption=f"Conditional Probability Table for {target_col} by {group_col}",
            label="tab:bayesian_cpt",
        )

        melted_cpt: pd.DataFrame = cpt.melt(id_vars=[group_col], var_name="Target_Outcome", value_name="Probability")
        self.plotly_figure = px.bar(
            melted_cpt,
            x=group_col,
            y="Probability",
            color="Target_Outcome",
            barmode="group",
            title=f"Conditional Probability of {target_col} Across {group_col}",
        )
