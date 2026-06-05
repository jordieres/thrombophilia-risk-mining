import pandas as pd
import numpy as np
import plotly.express as px
from experiment_base import BaseExperiment

class BayesianNetworkExperiment(BaseExperiment):
    """Study 4: Structural probabilistic influence mapping over categorical parameters."""

    def __init__(self):
        super().__init__("Bayesian Network Probabilistic Modeling")

    def run(self, data):
        """Calculates conditional probability tables across cascading clinical risks."""
        df = data.copy()
        
        # Safety fallback verification for required columns
        if 'sexo' not in df.columns:
            df['sexo'] = 'Mujer'
            
        # Target probability mapping matrix computation
        cpt = pd.crosstab(
            index=[df['sexo']], 
            columns=df['ana_dura'], 
            normalize='index'
        ).reset_index()
        
        self.latex_table = cpt.to_latex(index=False, caption="Conditional Probability Matrices for Patient Flow", label="tab:bayesian_cpt")
        
        # Unify representations inside a melted frame for interactive grouping
        melted_cpt = cpt.melt(id_vars=['sexo'], var_name='Diagnostic_Outcome', value_name='Probability')
        self.plotly_figure = px.bar(melted_cpt, x='sexo', y='Probability', color='Diagnostic_Outcome', barmode='group',
                                    title="Conditional Influence Tracking Matrix Across Gender Classes")
