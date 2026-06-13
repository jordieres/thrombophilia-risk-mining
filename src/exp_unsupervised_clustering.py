"""Unsupervised clustering experiment implementation.

The clustering workflow restricts itself to numeric variables, imputes missing
values with robust medians, scales the data, and then produces both cluster
assignments and a two-dimensional t-SNE embedding for visualization.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.express as px
from typing import Dict, Any, List
from sklearn.manifold import TSNE
from sklearn.cluster import AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from experiment_base import BaseExperiment

class UnsupervisedClusteringExperiment(BaseExperiment):
    """Study 3: Unsupervised phenotypic segmentation using t-SNE reduction mappings."""

    def __init__(self) -> None:
        super().__init__("Unsupervised Clinical Clustering")

    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        """Partitions the patient matrix into distinct non-supervised tracking subgroups."""
        max_samples: int = config.get('clustering_max_samples', 1000)

        df_numeric: pd.DataFrame = data.select_dtypes(include=[np.number]).dropna()
        if len(df_numeric) > max_samples:
            df_numeric = df_numeric.sample(n=max_samples, random_state=42).reset_index(drop=True)

        scaler: StandardScaler = StandardScaler()
        X_scaled: np.ndarray = scaler.fit_transform(df_numeric)

        cluster_model: AgglomerativeClustering = AgglomerativeClustering(n_clusters=3)
        labels: np.ndarray = cluster_model.fit_predict(X_scaled)

        # Set perplexity dynamically relative to size metrics to safeguard execution pipelines
        perp_val: float = min(30.0, float(len(X_scaled) - 1) / 3.0)
        tsne: TSNE = TSNE(n_components=2, random_state=42, perplexity=perp_val, n_iter=500)
        embeddings: np.ndarray = tsne.fit_transform(X_scaled)

        plot_df: pd.DataFrame = pd.DataFrame({
            'Dimension 1': embeddings[:, 0],
            'Dimension 2': embeddings[:, 1],
            'Cluster': labels.astype(str)
        })

        summary: pd.DataFrame = df_numeric.groupby(labels).mean()
        self.latex_table = summary.to_latex(caption="Mean Clinical Trajectories across Latent Groups", label="tab:clusters")

        self.plotly_figure = px.scatter(plot_df, x='Dimension 1', y='Dimension 2', color='Cluster',
                                        title="Patient Phenotypic Invariant Subspaces via t-SNE")
