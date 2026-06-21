"""Unsupervised clustering experiment implementation.

The clustering workflow restricts itself to numeric variables, imputes missing
values with robust medians, scales the data, applies agglomerative clustering,
and then produces a two-dimensional UMAP embedding for visualization.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

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
        output_dir: Path = Path(str(config.get("output_dir", ".")))
        color_rules_path_raw = config.get("clustering_color_rules_json")
        color_rules_path = Path(str(color_rules_path_raw)) if color_rules_path_raw else None

        working_df = data.copy()
        if "id_pacie" not in working_df.columns:
            working_df = working_df.copy()
            working_df["sample_index"] = np.arange(len(working_df))
        identifier_col = "id_pacie" if "id_pacie" in working_df.columns else "sample_index"

        df_numeric: pd.DataFrame = working_df.select_dtypes(include=[np.number]).copy()
        df_numeric = df_numeric.drop(columns=[identifier_col], errors="ignore")
        df_numeric = df_numeric.dropna(axis=1, how="all")

        if df_numeric.empty:
            raise ValueError("No numeric features are available for clustering after excluding empty columns.")

        imputer = SimpleImputer(strategy="median")
        imputed_numeric = pd.DataFrame(
            imputer.fit_transform(df_numeric),
            columns=df_numeric.columns,
            index=df_numeric.index,
        )

        if len(imputed_numeric) > max_samples:
            sampled_index = imputed_numeric.sample(n=max_samples, random_state=42).index
            sampled_numeric = imputed_numeric.loc[sampled_index].copy()
            sampled_metadata = working_df.loc[sampled_index].copy()
        else:
            sampled_numeric = imputed_numeric.copy()
            sampled_metadata = working_df.loc[imputed_numeric.index].copy()

        sampled_numeric = sampled_numeric.reset_index(drop=True)
        sampled_metadata = sampled_metadata.reset_index(drop=True)

        if len(sampled_numeric) < 2:
            raise ValueError("Clustering requires at least 2 samples after preprocessing.")

        scaler = StandardScaler()
        X_scaled: np.ndarray = scaler.fit_transform(sampled_numeric)

        n_clusters: int = max(2, min(requested_clusters, len(sampled_numeric)))
        linkage: str = "average" if metric_selection == "cosine" else "ward" if metric_selection == "euclidean" else "average"
        cluster_model = AgglomerativeClustering(
            n_clusters=n_clusters,
            metric=metric_selection,
            linkage=linkage,
        )
        labels: np.ndarray = cluster_model.fit_predict(X_scaled)

        n_neighbors: int = max(2, min(requested_neighbors, len(sampled_numeric) - 1))
        reducer = UMAP(
            n_components=2,
            metric=metric_selection,
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            random_state=42,
        )
        embeddings: np.ndarray = reducer.fit_transform(X_scaled)

        export_df = sampled_metadata.copy()
        export_df["umap_dimension_1"] = embeddings[:, 0]
        export_df["umap_dimension_2"] = embeddings[:, 1]
        export_df["cluster"] = labels.astype(str)
        export_df["color_group"] = self._build_color_groups(export_df=export_df, color_rules_path=color_rules_path)

        plot_df: pd.DataFrame = export_df[["umap_dimension_1", "umap_dimension_2", "cluster", "color_group"]].rename(
            columns={
                "umap_dimension_1": "Dimension 1",
                "umap_dimension_2": "Dimension 2",
                "cluster": "Cluster",
                "color_group": "Color Group",
            }
        )

        summary_df: pd.DataFrame = sampled_numeric.copy()
        summary_df["Cluster"] = labels
        feature_means: pd.DataFrame = summary_df.groupby("Cluster").mean(numeric_only=True)
        patient_counts: pd.Series = summary_df.groupby("Cluster").size().rename("Patient_Count")
        summary_clean: pd.DataFrame = patient_counts.to_frame().join(feature_means)

        self._export_umap_coordinates(export_df=export_df, output_dir=output_dir)

        self.latex_table = summary_clean.reset_index().to_latex(
            index=False,
            caption=f"Mean Clinical Trajectories and Sample Sizes via UMAP ({metric_selection.capitalize()} Space)",
            label="tab:clusters",
        )

        color_column = "Color Group" if color_rules_path is not None else "Cluster"
        self.plotly_figure = px.scatter(
            plot_df,
            x="Dimension 1",
            y="Dimension 2",
            color=color_column,
            title=f"Patient Phenotypic Invariant Subspaces via UMAP ({metric_selection.capitalize()} Metric)",
            hover_data={"Cluster": True, "Color Group": True},
        )

    def _build_color_groups(self, export_df: pd.DataFrame, color_rules_path: Path | None) -> pd.Series:
        """Assigns a color-group label per patient using an optional JSON ruleset."""
        if color_rules_path is None:
            return pd.Series("cluster", index=export_df.index, dtype="object")

        rules_payload = json.loads(color_rules_path.read_text(encoding="utf-8"))
        default_label = str(rules_payload.get("default", "other"))
        color_group = pd.Series(default_label, index=export_df.index, dtype="object")

        for rule in rules_payload.get("rules", []):
            label = str(rule.get("color", rule.get("label", "other")))
            mask = self._evaluate_rule(rule=rule, df=export_df)
            color_group = color_group.mask(mask, label)
        return color_group

    def _evaluate_rule(self, rule: Dict[str, Any], df: pd.DataFrame) -> pd.Series:
        """Evaluates one JSON color rule against the exported patient frame."""
        if "all" in rule:
            conditions = [self._evaluate_condition(condition, df) for condition in rule["all"]]
            return pd.concat(conditions, axis=1).all(axis=1) if conditions else pd.Series(False, index=df.index)
        if "any" in rule:
            conditions = [self._evaluate_condition(condition, df) for condition in rule["any"]]
            return pd.concat(conditions, axis=1).any(axis=1) if conditions else pd.Series(False, index=df.index)
        return self._evaluate_condition(rule, df)

    def _evaluate_condition(self, condition: Dict[str, Any], df: pd.DataFrame) -> pd.Series:
        """Evaluates one atomic JSON condition."""
        column = str(condition["var"])
        if column not in df.columns:
            return pd.Series(False, index=df.index)

        series = df[column]
        if "eq" in condition:
            return series.astype("string").eq(str(condition["eq"]))
        if "ne" in condition:
            return ~series.astype("string").eq(str(condition["ne"]))
        if "in" in condition:
            allowed = {str(value) for value in condition["in"]}
            return series.astype("string").isin(allowed)

        numeric_series = pd.to_numeric(series, errors="coerce")
        mask = pd.Series(True, index=df.index)
        if "gte" in condition:
            mask &= (numeric_series >= float(condition["gte"]))
        if "gt" in condition:
            mask &= (numeric_series > float(condition["gt"]))
        if "lte" in condition:
            mask &= (numeric_series <= float(condition["lte"]))
        if "lt" in condition:
            mask &= (numeric_series < float(condition["lt"]))
        return mask.fillna(False)

    def _export_umap_coordinates(self, export_df: pd.DataFrame, output_dir: Path) -> None:
        """Writes a reusable UMAP coordinate table linked to patient identifiers."""
        output_dir.mkdir(parents=True, exist_ok=True)
        export_df.to_csv(output_dir / "umap_coordinates.csv", index=False)
