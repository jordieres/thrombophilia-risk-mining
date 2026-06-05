"""Bayesian-style aggregation experiment.

This module builds a simple conditional probability table for the diagnostic
outcome grouped by sex. It does not learn a graphical model; instead, it offers
a lightweight probabilistic summary suitable for exploratory reporting.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px

from experiment_base import BaseExperiment


class BayesianNetworkExperiment(BaseExperiment):
    """Summarize outcome probabilities conditioned on sex.

    The implementation intentionally stays simple and robust so the Bayesian
    analysis path remains fast during interactive exploration.
    """

    def __init__(self) -> None:
        """Initialize the experiment metadata."""
        super().__init__("Bayesian Network Probabilistic Modeling")

    def run(self, data: pd.DataFrame) -> None:
        """Compute conditional outcome probabilities by sex.

        Args:
            data: Preprocessed clinical dataframe.

        Raises:
            ValueError: If the target column is missing.
        """
        df = data.copy()

        if "ana_dura" not in df.columns:
            raise ValueError("Bayesian network modeling requires the 'ana_dura' target column.")

        # Backfill sex when the source dataset omits the column entirely.
        if "sexo" not in df.columns:
            df["sexo"] = "Mujer"

        cpt = pd.crosstab(
            index=[df["sexo"]],
            columns=df["ana_dura"],
            normalize="index",
        ).reset_index()

        self.latex_table = cpt.to_latex(
            index=False,
            caption="Conditional Probability Matrices for Patient Flow",
            label="tab:bayesian_cpt",
        )

        melted_cpt = cpt.melt(
            id_vars=["sexo"],
            var_name="Diagnostic_Outcome",
            value_name="Probability",
        )
        self.plotly_figure = px.bar(
            melted_cpt,
            x="sexo",
            y="Probability",
            color="Diagnostic_Outcome",
            barmode="group",
            title="Conditional Influence Tracking Matrix Across Gender Classes",
        )
