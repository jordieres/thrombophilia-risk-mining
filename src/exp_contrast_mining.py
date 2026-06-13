"""Contrast-pattern mining experiment implementation.

This module builds transaction baskets from a constrained set of categorical
variables and then searches for association rules that are especially relevant
for positive and negative diagnostic outcomes.
"""

from __future__ import annotations
import pandas as pd
from typing import Dict, Any, List
import plotly.graph_objects as go
from mlxtend.frequent_patterns import fpgrowth, association_rules
from mlxtend.preprocessing import TransactionEncoder
from experiment_base import BaseExperiment

class ContrastPatternMiningExperiment(BaseExperiment):
    """Study 2: Sex-stratified contrast pattern discovery to map risk disparities."""

    def __init__(self) -> None:
        super().__init__("Contrast Pattern Mining")

    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        """Extracts and contrasts rule structures between positive and negative outcomes."""
        df: pd.DataFrame = data.copy()
        max_samples: int = config.get('contrast_max_samples', 300)

        if len(df) > max_samples:
            df = df.sample(n=max_samples, random_state=42).reset_index(drop=True)

        transactional_list: List[List[str]] = []
        for _, row in df.iterrows():
            items: List[str] = [f"{col}:{val}" for col, val in row.items() if col != 'id_pacie']
            transactional_list.append(items)

        te: TransactionEncoder = TransactionEncoder()
        te_ary: np.ndarray = te.fit(transactional_list).transform(transactional_list)
        df_trans: pd.DataFrame = pd.DataFrame(te_ary, columns=te.columns_)

        frequent_itemsets: pd.DataFrame = fpgrowth(df_trans, min_support=0.01, use_colnames=True)
        rules: pd.DataFrame = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.3)

        neg_rules: pd.DataFrame = rules[rules['consequents'].astype(str).str.contains("Buscada negativo")].head(3)
        pos_rules: pd.DataFrame = rules[rules['consequents'].astype(str).str.contains("Buscada positivo")].head(2)
        contrast_df: pd.DataFrame = pd.concat([neg_rules, pos_rules])

        contrast_df['Antecedents_Str'] = contrast_df['antecedents'].apply(lambda x: ', '.join(list(x)))
        contrast_df['Consequents_Str'] = contrast_df['consequents'].apply(lambda x: ', '.join(list(x)))

        export_cols: List[str] = ['Antecedents_Str', 'Consequents_Str', 'support', 'confidence', 'lift']
        self.latex_table = contrast_df[export_cols].to_latex(index=False, caption="Contrasting Behavioral Association Rules", label="tab:contrast")

        self.plotly_figure = go.Figure(data=[go.Scatter(
            x=contrast_df['support'], y=contrast_df['confidence'],
            mode='markers',
            marker=dict(size=14, color=contrast_df['lift'], colorscale='Plasma', showscale=True),
            text=contrast_df['Antecedents_Str']
        )])
        self.plotly_figure.update_layout(title="Contrast Pattern Distribution Space", xaxis_title="Support", yaxis_title="Confidence")
