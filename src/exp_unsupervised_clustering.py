import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.manifold import TSNE
from sklearn.cluster import AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from experiment_base import BaseExperiment

class UnsupervisedClusteringExperiment(BaseExperiment):
    """Study 3: Blind grouping and dimensional reduction to locate unexpected clinical subgroups."""

    def __init__(self):
        super().__init__("Unsupervised Clinical Clustering")

    def run(self, data):
        """Runs hierarchical clustering on numeric representations to identify latent profiles."""
        df = data.select_dtypes(include=[np.number]).dropna().head(1000)
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df)
        
        # Apply agglomerative clustering to locate clinical boundaries
        cluster_model = AgglomerativeClustering(n_clusters=3)
        labels = cluster_model.fit_predict(X_scaled)
        
        # Compress space using t-Distributed Stochastic Neighbor Embedding
        tsne = TSNE(n_components=2, random_state=42, perplexity=30)
        embeddings = tsne.fit_transform(X_scaled)
        
        plot_df = pd.DataFrame({
            'Dimension 1': embeddings[:, 0],
            'Dimension 2': embeddings[:, 1],
            'Cluster': labels.astype(str)
        })
        
        summary = df.groupby(labels).mean()
        self.latex_table = summary.to_latex(caption="Mean Clinical Trajectories across Latent Groups", label="tab:clusters")
        
        # Interactive scatter plot visualization
        self.plotly_figure = px.scatter(plot_df, x='Dimension 1', y='Dimension 2', color='Cluster',
                                        title="Patient Phenotypic Invariant Subspaces via t-SNE")
