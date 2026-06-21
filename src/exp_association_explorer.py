"""General association-rule explorer experiment implementation.

This module mines open association rules across bounded categorical variables,
allowing exploratory analysis beyond a single target outcome.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from mlxtend.frequent_patterns import association_rules, fpgrowth

from experiment_base import BaseExperiment


class AssociationExplorerExperiment(BaseExperiment):
    """Study 7: Open association-rule exploration across categorical variables."""

    def __init__(self) -> None:
        super().__init__("Association Explorer")

    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        """Mines general association rules and exports the strongest matches."""
        max_samples: int = int(config.get("association_rules_max_samples", 5000))
        min_support: float = float(config.get("association_rules_min_support", 0.01))
        min_confidence: float = float(config.get("association_rules_min_confidence", 0.4))
        min_lift: float = float(config.get("association_rules_min_lift", 1.0))
        max_feature_cardinality: int = int(config.get("association_rules_max_feature_cardinality", 12))
        max_features: int = int(config.get("association_rules_max_features", 24))
        max_rule_size: int = int(config.get("association_rules_max_rule_size", 3))
        top_k: int = int(config.get("association_rules_top_k", 30))
        sort_metric: str = str(config.get("association_rules_sort_metric", "leverage"))
        output_dir: Path = Path(str(config.get("output_dir", ".")))
        filter_column: str | None = config.get("association_rules_filter_column")
        filter_side: str = str(config.get("association_rules_filter_side", "either"))
        target_col: str | None = config.get("association_rules_target_column")
        valid_target_labels = [str(label) for label in config.get("association_rules_target_valid_labels", [])]
        resume: bool = bool(config.get("resume", False))

        if filter_side not in {"either", "antecedent", "consequent"}:
            raise ValueError("association_rules_filter_side must be one of: either, antecedent, consequent.")
        if sort_metric not in {"leverage", "lift", "confidence", "support"}:
            raise ValueError("association_rules_sort_metric must be one of: leverage, lift, confidence, support.")

        checkpoint_dir = self._build_checkpoint_dir(config)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(
            checkpoint_dir / "run_config.json",
            {
                "data": config.get("data"),
                "association_rules_max_samples": max_samples,
                "association_rules_min_support": min_support,
                "association_rules_min_confidence": min_confidence,
                "association_rules_min_lift": min_lift,
                "association_rules_max_feature_cardinality": max_feature_cardinality,
                "association_rules_max_features": max_features,
                "association_rules_max_rule_size": max_rule_size,
                "association_rules_top_k": top_k,
                "association_rules_sort_metric": sort_metric,
                "association_rules_filter_column": filter_column,
                "association_rules_filter_side": filter_side,
                "association_rules_target_column": target_col,
                "association_rules_target_valid_labels": valid_target_labels,
            },
        )

        prepared_path = checkpoint_dir / "01_prepared_sample.parquet"
        encoded_path = checkpoint_dir / "02_encoded_transactions.parquet"
        itemsets_path = checkpoint_dir / "03_frequent_itemsets.parquet"
        rules_path = checkpoint_dir / "04_association_rules.parquet"

        if resume and prepared_path.exists():
            prepared_df = pd.read_parquet(prepared_path)
        else:
            filtered_df = self._filter_target_rows(data, target_col=target_col, valid_target_labels=valid_target_labels)
            sampled_df = self._sample_rows(filtered_df, max_samples=max_samples)
            prepared_df, feature_profile = self._prepare_feature_frame(
                sampled_df,
                max_feature_cardinality=max_feature_cardinality,
                max_features=max_features,
                required_columns=[filter_column] if filter_column else None,
            )
            prepared_df.to_parquet(prepared_path, index=False)
            self._write_json(checkpoint_dir / "01_feature_profile.json", feature_profile)

        if resume and encoded_path.exists():
            encoded_df = pd.read_parquet(encoded_path).astype(bool)
        else:
            encoded_df = self._encode_transactions(prepared_df)
            encoded_df.astype(np.uint8).to_parquet(encoded_path, index=False)

        if resume and itemsets_path.exists():
            frequent_itemsets = self._load_itemsets(itemsets_path)
        else:
            frequent_itemsets = fpgrowth(
                encoded_df,
                min_support=min_support,
                use_colnames=True,
                max_len=max_rule_size,
            )
            frequent_itemsets = frequent_itemsets.sort_values(by=["support"], ascending=False).reset_index(drop=True)
            self._save_itemsets(frequent_itemsets, itemsets_path)

        if resume and rules_path.exists():
            rules_df = self._load_rules(rules_path)
        else:
            rules_df = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_confidence)
            rules_df = self._filter_rules(
                rules_df=rules_df,
                min_lift=min_lift,
                max_rule_size=max_rule_size,
                filter_column=filter_column,
                filter_side=filter_side,
            )
            self._save_rules(rules_df, rules_path)

        self._build_outputs(rules_df, sort_metric=sort_metric, top_k=top_k, output_dir=output_dir)

    def _build_checkpoint_dir(self, config: Dict[str, Any]) -> Path:
        checkpoint_root = Path(str(config.get("checkpoint_dir", "out/checkpoints")))
        dataset_label = Path(str(config.get("data", "dataset"))).stem
        fingerprint_fields = {
            "data": str(config.get("data", "dataset")),
            "association_rules_max_samples": config.get("association_rules_max_samples", 5000),
            "association_rules_min_support": config.get("association_rules_min_support", 0.01),
            "association_rules_min_confidence": config.get("association_rules_min_confidence", 0.4),
            "association_rules_min_lift": config.get("association_rules_min_lift", 1.0),
            "association_rules_max_feature_cardinality": config.get("association_rules_max_feature_cardinality", 12),
            "association_rules_max_features": config.get("association_rules_max_features", 24),
            "association_rules_max_rule_size": config.get("association_rules_max_rule_size", 3),
            "association_rules_filter_column": config.get("association_rules_filter_column"),
            "association_rules_filter_side": config.get("association_rules_filter_side", "either"),
            "association_rules_target_column": config.get("association_rules_target_column"),
            "association_rules_target_valid_labels": config.get("association_rules_target_valid_labels", []),
        }
        fingerprint = hashlib.sha1(json.dumps(fingerprint_fields, sort_keys=True).encode("utf-8")).hexdigest()[:12]
        return checkpoint_root / f"association_explorer_{dataset_label}_{fingerprint}"

    def _filter_target_rows(self, data: pd.DataFrame, target_col: str | None, valid_target_labels: List[str]) -> pd.DataFrame:
        if not target_col or not valid_target_labels:
            return data.copy()
        if target_col not in data.columns:
            raise ValueError(f"Association explorer requires the target column '{target_col}' when target filtering is requested.")
        filtered_df = data.copy()
        filtered_df[target_col] = filtered_df[target_col].astype("string")
        filtered_df = filtered_df[filtered_df[target_col].isin(valid_target_labels)].reset_index(drop=True)
        if filtered_df.empty:
            raise ValueError(f"No rows matched association_rules_target_valid_labels for target column '{target_col}'.")
        return filtered_df

    def _sample_rows(self, data: pd.DataFrame, max_samples: int) -> pd.DataFrame:
        if len(data) <= max_samples:
            return data.reset_index(drop=True).copy()
        return data.sample(n=max_samples, random_state=42).reset_index(drop=True).copy()

    def _prepare_feature_frame(
        self,
        data: pd.DataFrame,
        max_feature_cardinality: int,
        max_features: int,
        required_columns: List[str] | None = None,
    ) -> tuple[pd.DataFrame, Dict[str, Any]]:
        categorical_df = data.select_dtypes(include=["object", "category", "string"]).copy()
        categorical_df = categorical_df.drop(columns=["id_pacie"], errors="ignore")
        categorical_df = categorical_df.dropna(axis=1, how="all")
        candidates: List[Dict[str, Any]] = []

        for column in categorical_df.columns:
            unique_count = int(categorical_df[column].nunique(dropna=False))
            if unique_count < 2 or unique_count > max_feature_cardinality:
                continue
            candidates.append(
                {
                    "column": column,
                    "cardinality": unique_count,
                    "missing_rate": float(categorical_df[column].isna().mean()),
                }
            )

        candidates.sort(key=lambda item: (item["cardinality"], item["missing_rate"], item["column"]))
        selected_columns = [item["column"] for item in candidates[:max_features]]
        required_columns = [column for column in (required_columns or []) if column in categorical_df.columns]
        for required_column in required_columns:
            if required_column not in selected_columns:
                if len(selected_columns) >= max_features and max_features > 0:
                    selected_columns = selected_columns[:-1]
                selected_columns = [required_column] + selected_columns
        selected_columns = list(dict.fromkeys(selected_columns))
        if not selected_columns:
            raise ValueError(
                "Association explorer found no eligible low-cardinality categorical predictors. "
                "Increase --association-rules-max-feature-cardinality or inspect the dataset schema."
            )

        prepared_df = categorical_df[selected_columns].copy()
        for column in prepared_df.columns:
            prepared_df[column] = prepared_df[column].astype("object").where(prepared_df[column].notna(), "Missing").astype(str)

        feature_profile = {
            "selected_columns": selected_columns,
            "selected_feature_count": len(selected_columns),
            "max_feature_cardinality": max_feature_cardinality,
            "max_features": max_features,
            "candidate_profile": candidates,
        }
        return prepared_df, feature_profile

    def _encode_transactions(self, prepared_df: pd.DataFrame) -> pd.DataFrame:
        return pd.get_dummies(prepared_df, prefix_sep=":", sparse=True, dtype=np.uint8).astype(bool)

    def _filter_rules(
        self,
        rules_df: pd.DataFrame,
        min_lift: float,
        max_rule_size: int,
        filter_column: str | None,
        filter_side: str,
    ) -> pd.DataFrame:
        if rules_df.empty:
            return pd.DataFrame(columns=["antecedents", "consequents", "antecedent support", "consequent support", "support", "confidence", "lift", "leverage"])

        filtered_df = rules_df.copy()
        filtered_df = filtered_df[filtered_df["lift"] >= min_lift].copy()
        filtered_df["antecedent_len"] = filtered_df["antecedents"].apply(len)
        filtered_df["consequent_len"] = filtered_df["consequents"].apply(len)
        filtered_df = filtered_df[(filtered_df["antecedent_len"] >= 1) & (filtered_df["consequent_len"] >= 1)]
        filtered_df = filtered_df[(filtered_df["antecedent_len"] + filtered_df["consequent_len"]) <= max_rule_size].copy()

        if filter_column:
            prefix = f"{filter_column}:"
            in_antecedent = filtered_df["antecedents"].apply(lambda itemset: any(item.startswith(prefix) for item in itemset))
            in_consequent = filtered_df["consequents"].apply(lambda itemset: any(item.startswith(prefix) for item in itemset))
            if filter_side == "antecedent":
                filtered_df = filtered_df[in_antecedent].copy()
            elif filter_side == "consequent":
                filtered_df = filtered_df[in_consequent].copy()
            else:
                filtered_df = filtered_df[in_antecedent | in_consequent].copy()

        return filtered_df.reset_index(drop=True)

    def _build_outputs(self, rules_df: pd.DataFrame, sort_metric: str, top_k: int, output_dir: Path) -> None:
        if rules_df.empty:
            self.latex_table = pd.DataFrame(
                [{"Message": "No association rules satisfied the configured filters."}]
            ).to_latex(index=False, caption="Open Association Rules", label="tab:association_explorer")
            self.plotly_figure = go.Figure()
            self.plotly_figure.add_annotation(
                text="No rules satisfied the configured filters.",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
            )
            self.plotly_figure.update_layout(title="Association Rule Explorer")
            return

        display_df = rules_df.sort_values(by=[sort_metric, "confidence", "support"], ascending=False).head(top_k).reset_index(drop=True).copy()
        display_df["Antecedents_Str"] = display_df["antecedents"].apply(self._stringify_itemset)
        display_df["Consequents_Str"] = display_df["consequents"].apply(self._stringify_itemset)

        export_df = display_df[[
            "Antecedents_Str",
            "Consequents_Str",
            "support",
            "confidence",
            "lift",
            "leverage",
            "antecedent_len",
            "consequent_len",
        ]].rename(columns={
            "Antecedents_Str": "antecedents",
            "Consequents_Str": "consequents",
        })
        export_df.to_csv(output_dir / "association_explorer_top_rules.csv", index=False)

        self.latex_table = export_df.to_latex(
            index=False,
            caption="Open Association Rules Ranked by Configured Metric",
            label="tab:association_explorer",
        )

        self.plotly_figure = go.Figure(data=[go.Scatter(
            x=display_df["support"],
            y=display_df["confidence"],
            mode="markers",
            marker=dict(size=14, color=display_df["lift"], colorscale="Viridis", showscale=True),
            text=display_df["Antecedents_Str"],
            customdata=np.stack([
                display_df["Consequents_Str"],
                display_df["leverage"],
            ], axis=-1),
            hovertemplate=(
                "Antecedent: %{text}<br>"
                "Consequent: %{customdata[0]}<br>"
                "Support: %{x:.3f}<br>"
                "Confidence: %{y:.3f}<br>"
                "Lift: %{marker.color:.3f}<br>"
                "Leverage: %{customdata[1]:.3f}<extra></extra>"
            ),
        )])
        self.plotly_figure.update_layout(
            title="Association Rule Explorer",
            xaxis_title="Support",
            yaxis_title="Confidence",
        )

    def _save_itemsets(self, frequent_itemsets: pd.DataFrame, itemsets_path: Path) -> None:
        serializable_df = frequent_itemsets.copy()
        serializable_df["itemsets"] = serializable_df["itemsets"].apply(lambda itemset: json.dumps(sorted(itemset)))
        serializable_df.to_parquet(itemsets_path, index=False)

    def _load_itemsets(self, itemsets_path: Path) -> pd.DataFrame:
        frequent_itemsets = pd.read_parquet(itemsets_path)
        frequent_itemsets["itemsets"] = frequent_itemsets["itemsets"].apply(lambda raw: frozenset(json.loads(raw)))
        return frequent_itemsets

    def _save_rules(self, rules_df: pd.DataFrame, rules_path: Path) -> None:
        serializable_df = rules_df.copy()
        serializable_df["antecedents"] = serializable_df["antecedents"].apply(lambda itemset: json.dumps(sorted(itemset)))
        serializable_df["consequents"] = serializable_df["consequents"].apply(lambda itemset: json.dumps(sorted(itemset)))
        serializable_df.to_parquet(rules_path, index=False)

    def _load_rules(self, rules_path: Path) -> pd.DataFrame:
        rules_df = pd.read_parquet(rules_path)
        rules_df["antecedents"] = rules_df["antecedents"].apply(lambda raw: frozenset(json.loads(raw)))
        rules_df["consequents"] = rules_df["consequents"].apply(lambda raw: frozenset(json.loads(raw)))
        return rules_df

    def _write_json(self, output_path: Path, payload: Dict[str, Any]) -> None:
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _stringify_itemset(itemset: Iterable[str]) -> str:
        return ", ".join(sorted(itemset))
