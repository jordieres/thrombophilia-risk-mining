"""Contrast-pattern mining experiment implementation.

This module builds transaction baskets from a constrained set of categorical
variables and then searches for association rules that are especially relevant
for positive and negative diagnostic outcomes.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from mlxtend.frequent_patterns import association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder

from experiment_base import BaseExperiment


class ContrastPatternMiningExperiment(BaseExperiment):
    """Mine contrasting association rules for diagnostic outcomes.

    Attributes:
        max_samples: Maximum number of rows sampled for transaction mining.
        min_support: Minimum support threshold for frequent itemsets.
        max_features: Maximum number of categorical features kept in baskets.
        max_cardinality: Maximum allowed cardinality per categorical feature.
    """

    DEFAULT_MAX_SAMPLES = 300
    DEFAULT_MIN_SUPPORT = 0.08
    DEFAULT_MAX_FEATURES = 12
    DEFAULT_MAX_CARDINALITY = 5

    def __init__(
        self,
        max_samples: int | None = None,
        min_support: float | None = None,
        max_features: int | None = None,
        max_cardinality: int | None = None,
    ) -> None:
        """Initialize experiment parameters.

        Args:
            max_samples: Optional cap on sampled rows.
            min_support: Optional support threshold for FP-growth.
            max_features: Optional cap on selected categorical features.
            max_cardinality: Optional cap on feature cardinality.
        """
        super().__init__("Contrast Pattern Mining")
        self.max_samples: int = max_samples or self.DEFAULT_MAX_SAMPLES
        self.min_support: float = min_support or self.DEFAULT_MIN_SUPPORT
        self.max_features: int = max_features or self.DEFAULT_MAX_FEATURES
        self.max_cardinality: int = max_cardinality or self.DEFAULT_MAX_CARDINALITY

    def _sample_frame(self, frame: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """Draw a stratified sample for rule mining.

        Args:
            frame: Input dataframe.
            target_col: Name of the target column used for stratification.

        Returns:
            Sampled dataframe whose class proportions approximate the original.
        """
        if len(frame) <= self.max_samples:
            return frame.reset_index(drop=True)

        counts = frame[target_col].value_counts()
        sampled_parts: list[pd.DataFrame] = []
        remaining = self.max_samples

        for label, count in counts.items():
            label_frame = frame[frame[target_col] == label]
            label_quota = max(1, round(count * self.max_samples / len(frame)))
            label_quota = min(label_quota, len(label_frame), remaining)
            sampled_parts.append(label_frame.sample(n=label_quota, random_state=42))
            remaining -= label_quota

        sampled = pd.concat(sampled_parts)
        if len(sampled) < self.max_samples:
            extra = frame.drop(index=sampled.index).sample(
                n=self.max_samples - len(sampled),
                random_state=42,
            )
            sampled = pd.concat([sampled, extra])
        return sampled.reset_index(drop=True)

    def _select_categorical_features(self, frame: pd.DataFrame) -> list[str]:
        """Choose the categorical columns that will define transaction baskets.

        Args:
            frame: Sampled dataframe used by the contrast-mining experiment.

        Returns:
            Ordered list of low-cardinality categorical columns.
        """
        candidate_columns: list[str] = []
        for column in frame.columns:
            if column in {"id_pacie", "ana_dura"}:
                continue
            if pd.api.types.is_numeric_dtype(frame[column]):
                continue
            cardinality = frame[column].nunique(dropna=True)
            if 1 < cardinality <= self.max_cardinality:
                candidate_columns.append(column)
        return candidate_columns[: self.max_features]

    def run(self, data: pd.DataFrame) -> None:
        """Run the contrast-pattern mining workflow.

        Args:
            data: Preprocessed clinical dataframe.

        Raises:
            ValueError: If required columns are missing or the sampling and
                mining process cannot produce meaningful rules.
        """
        df = data.copy()

        if "ana_dura" not in df.columns:
            raise ValueError("Contrast mining requires the 'ana_dura' target column.")

        df = df[df["ana_dura"].notna()].copy()
        if df.empty:
            raise ValueError("Contrast mining requires non-null values in 'ana_dura'.")

        df = self._sample_frame(df, "ana_dura")
        candidate_columns = self._select_categorical_features(df)
        usable_columns = candidate_columns + ["ana_dura"]
        if len(usable_columns) <= 1:
            raise ValueError(
                "Contrast mining did not find enough low-cardinality categorical features to build transactions."
            )

        # Convert each row into a transaction made of "column:value" items.
        transactional_list: list[list[str]] = []
        for _, row in df[usable_columns].iterrows():
            items = [f"{column}:{value}" for column, value in row.fillna("Missing").items()]
            transactional_list.append(items)

        encoder = TransactionEncoder()
        encoded_transactions = encoder.fit(transactional_list).transform(transactional_list)
        transactions_df = pd.DataFrame(encoded_transactions, columns=encoder.columns_)

        frequent_itemsets = fpgrowth(transactions_df, min_support=self.min_support, use_colnames=True)
        if frequent_itemsets.empty:
            raise ValueError("Contrast mining did not find frequent itemsets with the current support threshold.")

        rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=0.4)
        if rules.empty:
            raise ValueError("Contrast mining did not produce association rules from the sampled data.")

        negative_rules = rules[rules["consequents"].astype(str).str.contains("Buscada negativo")].head(5)
        positive_rules = rules[rules["consequents"].astype(str).str.contains("Buscada positivo")].head(5)
        contrast_df = pd.concat([negative_rules, positive_rules]).drop_duplicates().reset_index(drop=True)
        if contrast_df.empty:
            raise ValueError(
                "Contrast mining did not find rules pointing to 'Buscada negativo' or 'Buscada positivo'."
            )

        contrast_df["Antecedents_Str"] = contrast_df["antecedents"].apply(lambda items: ", ".join(list(items)))
        contrast_df["Consequents_Str"] = contrast_df["consequents"].apply(lambda items: ", ".join(list(items)))

        export_columns = ["Antecedents_Str", "Consequents_Str", "support", "confidence", "lift"]
        self.latex_table = contrast_df[export_columns].to_latex(
            index=False,
            caption="Contrasting Behavioral Association Rules",
            label="tab:contrast",
        )

        self.plotly_figure = go.Figure(
            data=[
                go.Scatter(
                    x=contrast_df["support"],
                    y=contrast_df["confidence"],
                    mode="markers",
                    marker=dict(
                        size=12,
                        color=contrast_df["lift"],
                        colorscale="Viridis",
                        showscale=True,
                    ),
                    text=contrast_df["Antecedents_Str"],
                )
            ]
        )
        self.plotly_figure.update_layout(
            title="Contrast Pattern Distribution Space",
            xaxis_title="Support",
            yaxis_title="Confidence",
        )
