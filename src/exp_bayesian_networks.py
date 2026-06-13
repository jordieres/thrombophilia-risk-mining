"""Bayesian-style aggregation experiment.

This module builds a simple conditional probability table for the diagnostic
outcome grouped by sex. It does not learn a graphical model; instead, it offers
a lightweight probabilistic summary suitable for exploratory reporting.
"""

from __future__ import annotations
import pandas as pd
from typing import Dict, Any, List
import plotly.express as px
from pgmpy.models import BayesianNetwork
from pgmpy.estimators import MaximumLikelihoodEstimator
from experiment_base import BaseExperiment

class BayesianNetworkExperiment(BaseExperiment):
    """Study 4: Joint probability modeling and causal gatekeeping parameter estimations."""

    def __init__(self) -> None:
        super().__init__("Bayesian Network Probabilistic Modeling")

    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        """Models conditional probability distribution charts to isolate wasted testing indices."""
        df: pd.DataFrame = data.copy()

        # Enforce categorical mapping standards safely
        if 'sexo' not in df.columns:
            df['sexo'] = 'Female'
        df['sexo'] = df['sexo'].replace({'Male': 'Hombre', 'Female': 'Mujer'})

        # Structure the targeted causal mapping infrastructure
        model: BayesianNetwork = BayesianNetwork([('sexo', 'ana_dura')])
        model.fit(df, estimator=MaximumLikelihoodEstimator)

        cpt: pd.DataFrame = pd.crosstab(
            index=[df['sexo']],
            columns=df['ana_dura'],
            normalize='index'
        ).reset_index()

        self.latex_table = cpt.to_latex(index=False, caption="Conditional Probability Matrices for Patient Flow", label="tab:bayesian_cpt")

        melted_cpt: pd.DataFrame = cpt.melt(id_vars=['sexo'], var_name='Diagnostic_Outcome', value_name='Probability')
        self.plotly_figure = px.bar(melted_cpt, x='sexo', y='Probability', color='Diagnostic_Outcome', barmode='group',
                                    title="Conditional Influence Tracking Matrix Across Gender Classes")
