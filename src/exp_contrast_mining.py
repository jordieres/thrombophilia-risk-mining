import pandas as pd
import plotly.graph_objects as go
from mlxtend.frequent_patterns import fpgrowth, association_rules
from mlxtend.preprocessing import TransactionEncoder
from experiment_base import BaseExperiment

class ContrastPatternMiningExperiment(BaseExperiment):
    """Study 2: Contrast pattern discovery isolating behavioral discrepancies between outcomes."""

    def __init__(self):
        super().__init__("Contrast Pattern Mining")

    def run(self, data):
        """Extracts and contrasts rule structures between positive and negative outcomes."""
        df = data.copy()
        
        # Prepare list-based transactional entries for tree extraction
        transactional_list = []
        for _, row in df.iterrows():
            items = [f"{col}:{val}" for col, val in row.items() if col != 'id_pacie']
            transactional_list.append(items)
            
        te = TransactionEncoder()
        te_ary = te.fit(transactional_list).transform(transactional_list)
        df_trans = pd.DataFrame(te_ary, columns=te.columns_)
        
        frequent_itemsets = fpgrowth(df_trans, min_support=0.005, use_colnames=True)
        rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.4)
        
        # Filter directional patterns explaining specific outcome boundaries
        neg_rules = rules[rules['consequents'].astype(str).str.contains("Buscada negativo")].head(5)
        pos_rules = rules[rules['consequents'].astype(str).str.contains("Buscada positivo")].head(5)
        contrast_df = pd.concat([neg_rules, pos_rules])
        
        # Build out clean string columns for visual exporting
        contrast_df['Antecedents_Str'] = contrast_df['antecedents'].apply(lambda x: ', '.join(list(x)))
        contrast_df['Consequents_Str'] = contrast_df['consequents'].apply(lambda x: ', '.join(list(x)))
        
        export_cols = ['Antecedents_Str', 'Consequents_Str', 'support', 'confidence', 'lift']
        self.latex_table = contrast_df[export_cols].to_latex(index=False, caption="Contrasting Behavioral Association Rules", label="tab:contrast")
        
        # Create an interactive Plotly scatter layout mapping the rules
        self.plotly_figure = go.Figure(data=[go.Scatter(
            x=contrast_df['support'], y=contrast_df['confidence'],
            mode='markers',
            marker=dict(size=12, color=contrast_df['lift'], colorscale='Viridis', showscale=True),
            text=contrast_df['Antecedents_Str']
        )])
        self.plotly_figure.update_layout(title="Contrast Pattern Distribution Space", xaxis_title="Support", yaxis_title="Confidence")
