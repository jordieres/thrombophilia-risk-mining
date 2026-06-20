"""Unsupervised clustering experiment implementation.

The clustering workflow restricts itself to numeric variables, imputes missing
values with robust medians, scales the data, applies agglomerative clustering,
and then produces a two-dimensional UMAP embedding for visualization.
"""

from __future__ import annotations

from typing import Any, Dict, List
import sys

import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.cluster import AgglomerativeClustering
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

# Force classic UMAP import path to skip parametric torchvision dependencies.
if "torchvision" not in sys.modules:
    sys.modules["torchvision"] = None

from umap import UMAP

from experiment_base import BaseExperiment


class UnsupervisedClusteringExperiment(BaseExperiment):
    """Study 3: Unsupervised phenotypic segmentation using UMAP reduction mappings."""

    def __init__(self) -> None:
        super().__init__("Unsupervised Clinical Clustering")

    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        """Partitions the patient matrix into distinct non-supervised tracking subgroups."""
        max_samples: int = int(config.get("clustering_max_samples", 1000))
        metric_selection: str = str(config.get("clustering_metric", "manhattan"))
        requested_clusters: int = int(config.get("clustering_n_clusters", 3))
        requested_neighbors: int = int(config.get("clustering_n_neighbors", 15))
        min_dist: float = float(config.get("clustering_min_dist", 0.1))

        df_numeric: pd.DataFrame = data.select_dtypes(include=[np.number]).copy()
        df_numeric = df_numeric.drop(columns=["id_pacie"], errors="ignore")
        df_numeric = df_numeric.dropna(axis=1, how="all")

        if df_numeric.empty:
            raise ValueError("No numeric features are available for clustering after excluding empty columns.")

        imputer = SimpleImputer(strategy="median")
        df_numeric = pd.DataFrame(
            imputer.fit_transform(df_numeric),
            columns=df_numeric.columns,
            index=df_numeric.index,
        )

        if len(df_numeric) > max_samples:
            df_numeric = df_numeric.sample(n=max_samples, random_state=42).reset_index(drop=True)

        if len(df_numeric) < 2:
            raise ValueError("Clustering requires at least 2 samples after preprocessing.")

        scaler = StandardScaler()
        X_scaled: np.ndarray = scaler.fit_transform(df_numeric)

        n_clusters: int = max(2, min(requested_clusters, len(df_numeric)))
        linkage: str = "average" if metric_selection == "cosine" else "ward" if metric_selection == "euclidean" else "average"
        cluster_model = AgglomerativeClustering(
            n_clusters=n_clusters,
            metric=metric_selection,
            linkage=linkage,
        )
        labels: np.ndarray = cluster_model.fit_predict(X_scaled)

        n_neighbors: int = max(2, min(requested_neighbors, len(df_numeric) - 1))
        reducer = UMAP(
            n_components=2,
            metric=metric_selection,
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            random_state=42,
        )
        embeddings: np.ndarray = reducer.fit_transform(X_scaled)

        plot_df: pd.DataFrame = pd.DataFrame(
            {
                "Dimension 1": embeddings[:, 0],
                "Dimension 2": embeddings[:, 1],
                "Cluster": labels.astype(str),
            }
        )

        summary_df: pd.DataFrame = df_numeric.copy()
        summary_df["Cluster"] = labels
        feature_means: pd.DataFrame = summary_df.groupby("Cluster").mean(numeric_only=True)
        patient_counts: pd.Series = summary_df.groupby("Cluster").size().rename("Patient_Count")
        summary_clean: pd.DataFrame = patient_counts.to_frame().join(feature_means)

        self.latex_table = summary_clean.reset_index().to_latex(
            index=False,
            caption=f"Mean Clinical Trajectories and Sample Sizes via UMAP ({metric_selection.capitalize()} Space)",
            label="tab:clusters",
        )

        self.plotly_figure = px.scatter(
            plot_df,
            x="Dimension 1",
            y="Dimension 2",
            color="Cluster",
            title=f"Patient Phenotypic Invariant Subspaces via UMAP ({metric_selection.capitalize()} Metric)",
        )
