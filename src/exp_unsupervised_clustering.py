"""Unsupervised clustering experiment implementation.

The clustering workflow restricts itself to numeric variables, imputes missing
values with robust medians, scales the data, and then produces both cluster
assignments and a two-dimensional t-SNE embedding for visualization.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.cluster import AgglomerativeClustering
from sklearn.impute import SimpleImputer
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler

from experiment_base import BaseExperiment


class UnsupervisedClusteringExperiment(BaseExperiment):
    """Discover latent numeric patient subgroups.

    Attributes:
        max_samples: Maximum number of rows retained for the experiment.
        n_clusters: Requested number of agglomerative clusters.
        max_perplexity: Upper bound applied to the t-SNE perplexity parameter.
    """

    DEFAULT_MAX_SAMPLES = 1000
    DEFAULT_N_CLUSTERS = 3
    DEFAULT_MAX_PERPLEXITY = 30

    def __init__(
        self,
        max_samples: int | None = None,
        n_clusters: int | None = None,
        max_perplexity: int | None = None,
    ) -> None:
        """Initialize experiment parameters.

        Args:
            max_samples: Optional row cap used before clustering.
            n_clusters: Optional requested number of clusters.
            max_perplexity: Optional upper bound for the t-SNE perplexity.
        """
        super().__init__("Unsupervised Clinical Clustering")
        self.max_samples: int = max_samples or self.DEFAULT_MAX_SAMPLES
        self.n_clusters: int = n_clusters or self.DEFAULT_N_CLUSTERS
        self.max_perplexity: int = max_perplexity or self.DEFAULT_MAX_PERPLEXITY

    def run(self, data: pd.DataFrame) -> None:
        """Run the clustering and visualization workflow.

        Args:
            data: Preprocessed clinical dataframe.

        Raises:
            ValueError: If the numeric subset is empty or too small to cluster.
        """
        df = data.select_dtypes(include=[np.number]).copy().head(self.max_samples)
        df = df.dropna(axis=1, how="all")

        if df.empty:
            raise ValueError("Clustering requires at least one numeric column after preprocessing.")

        # Median imputation preserves row count for sparse clinical measurements.
        imputer = SimpleImputer(strategy="median")
        imputed = imputer.fit_transform(df)
        imputed_df = pd.DataFrame(imputed, columns=df.columns, index=df.index)

        sample_count = len(imputed_df)
        if sample_count < 3:
            raise ValueError("Clustering requires at least three rows after numeric preprocessing.")

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(imputed_df)

        cluster_model = AgglomerativeClustering(n_clusters=min(self.n_clusters, sample_count))
        labels = cluster_model.fit_predict(X_scaled)

        embedding_model = TSNE(
            n_components=2,
            random_state=42,
            perplexity=min(self.max_perplexity, sample_count - 1),
        )
        embeddings = embedding_model.fit_transform(X_scaled)

        plot_df = pd.DataFrame(
            {
                "Dimension 1": embeddings[:, 0],
                "Dimension 2": embeddings[:, 1],
                "Cluster": labels.astype(str),
            }
        )

        summary = imputed_df.groupby(labels).mean()
        self.latex_table = summary.to_latex(
            caption="Mean Clinical Trajectories across Latent Groups",
            label="tab:clusters",
        )

        self.plotly_figure = px.scatter(
            plot_df,
            x="Dimension 1",
            y="Dimension 2",
            color="Cluster",
            title="Patient Phenotypic Invariant Subspaces via t-SNE",
        )
