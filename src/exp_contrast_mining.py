"""Contrast-pattern mining experiment implementation.

This module constrains the transactional search space to low-cardinality
variables, mines frequent itemsets over a sparse one-hot matrix, and derives
only outcome-targeted rules so the memory footprint remains bounded on large
clinical datasets.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import gc
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from mlxtend.frequent_patterns import fpgrowth
from experiment_base import BaseExperiment


def _extract_target_rules(
    target_item: str,
    itemset_records: List[Tuple[frozenset[str], float]],
    support_map: Dict[frozenset[str], float],
    min_confidence: float,
    top_k: int,
) -> pd.DataFrame:
    """Builds rules whose consequent is a single requested outcome item."""
    target_key: frozenset[str] = frozenset([target_item])
    target_support: float = float(support_map.get(target_key, 0.0))
    rows: List[Dict[str, Any]] = []

    if target_support <= 0.0:
        return pd.DataFrame(columns=['antecedents', 'consequents', 'support', 'confidence', 'lift'])

    for itemset, support in itemset_records:
        if target_item not in itemset or len(itemset) < 2:
            continue

        antecedents: frozenset[str] = frozenset(item for item in itemset if item != target_item)
        antecedent_support: float = float(support_map.get(antecedents, 0.0))
        if antecedent_support <= 0.0:
            continue

        confidence: float = float(support / antecedent_support)
        if confidence < min_confidence:
            continue

        lift: float = float(confidence / target_support)
        rows.append({
            'antecedents': antecedents,
            'consequents': target_key,
            'support': float(support),
            'confidence': confidence,
            'lift': lift,
        })

    if not rows:
        return pd.DataFrame(columns=['antecedents', 'consequents', 'support', 'confidence', 'lift'])

    rules_df: pd.DataFrame = pd.DataFrame(rows)
    return rules_df.sort_values(by=['lift', 'confidence', 'support'], ascending=False).head(top_k).reset_index(drop=True)


class ContrastPatternMiningExperiment(BaseExperiment):
    """Study 2: Sex-stratified contrast pattern discovery to map risk disparities."""

    def __init__(self) -> None:
        super().__init__("Contrast Pattern Mining")

    def run(self, data: pd.DataFrame, config: Dict[str, Any]) -> None:
        """Extracts targeted contrast rules while checkpointing each major stage."""
        target_col: str = str(config.get('contrast_target_column', 'ana_dura'))
        valid_target_labels = [str(label) for label in config.get('contrast_target_valid_labels', [])]
        max_samples: int = int(config.get('contrast_max_samples', 300))
        min_support: float = float(config.get('contrast_min_support', 0.05))
        min_confidence: float = float(config.get('contrast_min_confidence', 0.4))
        max_feature_cardinality: int = int(config.get('contrast_max_feature_cardinality', 12))
        max_features: int = int(config.get('contrast_max_features', 48))
        max_rule_size: int = int(config.get('contrast_max_rule_size', 3))
        top_k: int = int(config.get('contrast_top_k_per_outcome', 5))
        requested_workers: int = int(config.get('contrast_workers', 2))
        resume: bool = bool(config.get('resume', False))

        checkpoint_dir: Path = self._build_checkpoint_dir(config)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(
            checkpoint_dir / 'run_config.json',
            {
                'data': config.get('data'),
                'contrast_target_column': target_col,
                'contrast_target_valid_labels': valid_target_labels,
                'contrast_max_samples': max_samples,
                'contrast_min_support': min_support,
                'contrast_min_confidence': min_confidence,
                'contrast_max_feature_cardinality': max_feature_cardinality,
                'contrast_max_features': max_features,
                'contrast_max_rule_size': max_rule_size,
                'contrast_top_k_per_outcome': top_k,
                'contrast_workers': requested_workers,
            },
        )

        prepared_path: Path = checkpoint_dir / '01_prepared_sample.parquet'
        encoded_path: Path = checkpoint_dir / '02_encoded_transactions.parquet'
        itemsets_path: Path = checkpoint_dir / '03_frequent_itemsets.parquet'
        rules_path: Path = checkpoint_dir / '04_target_rules.parquet'

        prepared_df: pd.DataFrame
        if resume and prepared_path.exists():
            prepared_df = pd.read_parquet(prepared_path)
        else:
            filtered_df = self._filter_target_rows(data, target_col=target_col, valid_target_labels=valid_target_labels)
            sampled_df = self._sample_rows(filtered_df, target_col=target_col, max_samples=max_samples)
            prepared_df, feature_profile = self._prepare_feature_frame(
                sampled_df,
                target_col=target_col,
                max_feature_cardinality=max_feature_cardinality,
                max_features=max_features,
            )
            prepared_df.to_parquet(prepared_path, index=False)
            self._write_json(checkpoint_dir / '01_feature_profile.json', feature_profile)
            del sampled_df
            gc.collect()

        encoded_df: pd.DataFrame
        if resume and encoded_path.exists():
            encoded_df = pd.read_parquet(encoded_path).astype(bool)
        else:
            encoded_df = self._encode_transactions(prepared_df)
            encoded_df.astype(np.uint8).to_parquet(encoded_path, index=False)
            gc.collect()

        frequent_itemsets: pd.DataFrame
        if resume and itemsets_path.exists():
            frequent_itemsets = self._load_itemsets(itemsets_path)
        else:
            frequent_itemsets = fpgrowth(
                encoded_df,
                min_support=min_support,
                use_colnames=True,
                max_len=max_rule_size,
            )
            frequent_itemsets = frequent_itemsets.sort_values(by=['support'], ascending=False).reset_index(drop=True)
            self._save_itemsets(frequent_itemsets, itemsets_path)
            gc.collect()

        contrast_df: pd.DataFrame
        if resume and rules_path.exists():
            contrast_df = self._load_rules(rules_path)
        else:
            contrast_df = self._build_target_rules(
                prepared_df=prepared_df,
                frequent_itemsets=frequent_itemsets,
                target_col=target_col,
                min_confidence=min_confidence,
                top_k=top_k,
                requested_workers=requested_workers,
            )
            self._save_rules(contrast_df, rules_path)
            gc.collect()

        self._build_outputs(contrast_df)

    def _build_checkpoint_dir(self, config: Dict[str, Any]) -> Path:
        """Creates a stable checkpoint directory derived from dataset and budgets."""
        checkpoint_root: Path = Path(str(config.get('checkpoint_dir', 'out/checkpoints')))
        dataset_label: str = Path(str(config.get('data', 'dataset'))).stem
        fingerprint_fields: Dict[str, Any] = {
            'data': str(config.get('data', 'dataset')),
            'contrast_target_column': config.get('contrast_target_column', 'ana_dura'),
            'contrast_target_valid_labels': config.get('contrast_target_valid_labels', []),
            'contrast_max_samples': config.get('contrast_max_samples', 300),
            'contrast_min_support': config.get('contrast_min_support', 0.05),
            'contrast_min_confidence': config.get('contrast_min_confidence', 0.4),
            'contrast_max_feature_cardinality': config.get('contrast_max_feature_cardinality', 12),
            'contrast_max_features': config.get('contrast_max_features', 48),
            'contrast_max_rule_size': config.get('contrast_max_rule_size', 3),
        }
        fingerprint: str = hashlib.sha1(json.dumps(fingerprint_fields, sort_keys=True).encode('utf-8')).hexdigest()[:12]
        return checkpoint_root / f"contrast_pattern_mining_{dataset_label}_{fingerprint}"

    def _filter_target_rows(self, data: pd.DataFrame, target_col: str, valid_target_labels: List[str]) -> pd.DataFrame:
        if target_col not in data.columns:
            raise ValueError(f"Contrast mining requires the target column '{target_col}'.")
        if not valid_target_labels:
            return data.copy()
        filtered_df = data.copy()
        filtered_df[target_col] = filtered_df[target_col].astype('string')
        filtered_df = filtered_df[filtered_df[target_col].isin(valid_target_labels)].reset_index(drop=True)
        if filtered_df.empty:
            raise ValueError(f"No rows matched contrast_target_valid_labels for target column '{target_col}'.")
        return filtered_df

    def _sample_rows(self, data: pd.DataFrame, target_col: str, max_samples: int) -> pd.DataFrame:
        """Samples rows while preserving outcome proportions when possible."""
        if len(data) <= max_samples:
            return data.reset_index(drop=True).copy()

        if target_col not in data.columns or data[target_col].nunique(dropna=False) < 2:
            return data.sample(n=max_samples, random_state=42).reset_index(drop=True).copy()

        group_sizes: pd.Series = data[target_col].value_counts(dropna=False)
        raw_allocations: pd.Series = group_sizes / group_sizes.sum() * max_samples
        base_allocations: Dict[Any, int] = {
            label: min(int(np.floor(size)), int(group_sizes[label]))
            for label, size in raw_allocations.items()
        }

        for label in group_sizes.index:
            if base_allocations[label] == 0 and group_sizes[label] > 0:
                base_allocations[label] = 1

        allocated: int = sum(base_allocations.values())
        if allocated > max_samples:
            overflow: int = allocated - max_samples
            for label in sorted(group_sizes.index, key=lambda key: base_allocations[key], reverse=True):
                if overflow == 0:
                    break
                removable: int = max(0, base_allocations[label] - 1)
                reduction: int = min(removable, overflow)
                base_allocations[label] -= reduction
                overflow -= reduction
        elif allocated < max_samples:
            remainders: List[Tuple[float, Any]] = []
            for label, raw_value in raw_allocations.items():
                spare_capacity: int = int(group_sizes[label] - base_allocations[label])
                if spare_capacity > 0:
                    remainders.append((float(raw_value - np.floor(raw_value)), label))
            remainders.sort(reverse=True)
            remaining: int = max_samples - allocated
            while remaining > 0 and remainders:
                next_round: List[Tuple[float, Any]] = []
                for fractional_part, label in remainders:
                    if remaining == 0:
                        next_round.append((fractional_part, label))
                        continue
                    if base_allocations[label] < int(group_sizes[label]):
                        base_allocations[label] += 1
                        remaining -= 1
                    if base_allocations[label] < int(group_sizes[label]):
                        next_round.append((fractional_part, label))
                if len(next_round) == len(remainders):
                    break
                remainders = next_round

        sampled_groups: List[pd.DataFrame] = []
        for label, requested_rows in base_allocations.items():
            if requested_rows <= 0:
                continue

            if pd.isna(label):
                group_df = data[data[target_col].isna()]
            else:
                group_df = data[data[target_col] == label]

            if group_df.empty:
                continue

            sampled_groups.append(group_df.sample(n=min(requested_rows, len(group_df)), random_state=42))

        sampled_df: pd.DataFrame = pd.concat(sampled_groups, ignore_index=True)
        return sampled_df.sample(frac=1.0, random_state=42).reset_index(drop=True)

    def _prepare_feature_frame(
        self,
        data: pd.DataFrame,
        target_col: str,
        max_feature_cardinality: int,
        max_features: int,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Selects low-cardinality columns to keep transactional mining bounded."""
        if target_col not in data.columns:
            raise ValueError(f"Contrast mining requires the target column '{target_col}'.")

        excluded_columns: set[str] = {'id_pacie', target_col}
        candidates: List[Dict[str, Any]] = []

        for column in data.columns:
            if column in excluded_columns:
                continue

            unique_count: int = int(data[column].nunique(dropna=False))
            if unique_count < 2 or unique_count > max_feature_cardinality:
                continue

            missing_rate: float = float(data[column].isna().mean())
            candidates.append({
                'column': column,
                'cardinality': unique_count,
                'missing_rate': missing_rate,
            })

        candidates.sort(key=lambda item: (item['cardinality'], item['missing_rate'], item['column']))
        selected_feature_cols: List[str] = [item['column'] for item in candidates[:max_features]]
        if not selected_feature_cols:
            raise ValueError(
                "Contrast mining found no eligible low-cardinality predictors. "
                "Increase --contrast-max-feature-cardinality or inspect the dataset schema."
            )

        selected_columns: List[str] = [target_col] + selected_feature_cols
        prepared_df: pd.DataFrame = data.loc[:, selected_columns].copy()
        for column in prepared_df.columns:
            prepared_df[column] = prepared_df[column].astype('string').fillna('Missing').astype(str)

        feature_profile: Dict[str, Any] = {
            'target_column': target_col,
            'selected_columns': selected_columns,
            'selected_feature_count': len(selected_feature_cols),
            'max_feature_cardinality': max_feature_cardinality,
            'max_features': max_features,
            'dropped_high_cardinality_columns': [
                column for column in data.columns
                if column not in selected_columns and column != 'id_pacie'
            ],
            'candidate_profile': candidates,
        }
        return prepared_df, feature_profile

    def _encode_transactions(self, prepared_df: pd.DataFrame) -> pd.DataFrame:
        """Builds a sparse transactional matrix using bounded categorical columns."""
        encoded_df: pd.DataFrame = pd.get_dummies(
            prepared_df,
            prefix_sep=':',
            sparse=True,
            dtype=np.uint8,
        )
        return encoded_df.astype(bool)

    def _build_target_rules(
        self,
        prepared_df: pd.DataFrame,
        frequent_itemsets: pd.DataFrame,
        target_col: str,
        min_confidence: float,
        top_k: int,
        requested_workers: int,
    ) -> pd.DataFrame:
        """Derives only rules that conclude in a diagnostic outcome item."""
        target_items: List[str] = [f"{target_col}:{value}" for value in sorted(prepared_df[target_col].unique())]
        support_map: Dict[frozenset[str], float] = {
            frozenset(itemset): float(support)
            for itemset, support in zip(frequent_itemsets['itemsets'], frequent_itemsets['support'])
        }
        itemset_records: List[Tuple[frozenset[str], float]] = [
            (frozenset(itemset), float(support))
            for itemset, support in zip(frequent_itemsets['itemsets'], frequent_itemsets['support'])
        ]

        worker_count: int = max(1, min(len(target_items), requested_workers, os.cpu_count() or 1))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            rule_frames: List[pd.DataFrame] = list(
                executor.map(
                    lambda target_item: _extract_target_rules(
                        target_item=target_item,
                        itemset_records=itemset_records,
                        support_map=support_map,
                        min_confidence=min_confidence,
                        top_k=top_k,
                    ),
                    target_items,
                )
            )

        contrast_df: pd.DataFrame = pd.concat(rule_frames, ignore_index=True) if rule_frames else pd.DataFrame()
        if contrast_df.empty:
            return pd.DataFrame(columns=['antecedents', 'consequents', 'support', 'confidence', 'lift'])

        return contrast_df.sort_values(by=['lift', 'confidence', 'support'], ascending=False).reset_index(drop=True)

    def _build_outputs(self, contrast_df: pd.DataFrame) -> None:
        """Formats LaTeX and visualization artifacts from mined rules."""
        if contrast_df.empty:
            self.latex_table = pd.DataFrame(
                [{'Message': 'No contrast rules satisfied the configured support and confidence thresholds.'}]
            ).to_latex(index=False, caption="Contrasting Behavioral Association Rules", label="tab:contrast")
            self.plotly_figure = go.Figure()
            self.plotly_figure.add_annotation(
                text="No rules satisfied the configured thresholds.",
                x=0.5,
                y=0.5,
                xref='paper',
                yref='paper',
                showarrow=False,
            )
            self.plotly_figure.update_layout(title="Contrast Pattern Distribution Space")
            return

        formatted_df: pd.DataFrame = contrast_df.copy()
        formatted_df['Antecedents_Str'] = formatted_df['antecedents'].apply(self._stringify_itemset)
        formatted_df['Consequents_Str'] = formatted_df['consequents'].apply(self._stringify_itemset)

        export_cols: List[str] = ['Antecedents_Str', 'Consequents_Str', 'support', 'confidence', 'lift']
        self.latex_table = formatted_df[export_cols].to_latex(
            index=False,
            caption="Contrasting Behavioral Association Rules",
            label="tab:contrast",
        )

        self.plotly_figure = go.Figure(data=[go.Scatter(
            x=formatted_df['support'],
            y=formatted_df['confidence'],
            mode='markers',
            marker=dict(size=14, color=formatted_df['lift'], colorscale='Plasma', showscale=True),
            text=formatted_df['Antecedents_Str'],
            customdata=formatted_df[['Consequents_Str']],
            hovertemplate=(
                "Antecedent: %{text}<br>"
                "Consequent: %{customdata[0]}<br>"
                "Support: %{x:.3f}<br>"
                "Confidence: %{y:.3f}<br>"
                "Lift: %{marker.color:.3f}<extra></extra>"
            ),
        )])
        self.plotly_figure.update_layout(
            title="Contrast Pattern Distribution Space",
            xaxis_title="Support",
            yaxis_title="Confidence",
        )

    def _save_itemsets(self, frequent_itemsets: pd.DataFrame, itemsets_path: Path) -> None:
        """Persists frequent itemsets using JSON-serializable list columns."""
        serializable_df: pd.DataFrame = frequent_itemsets.copy()
        serializable_df['itemsets'] = serializable_df['itemsets'].apply(lambda itemset: json.dumps(sorted(itemset)))
        serializable_df.to_parquet(itemsets_path, index=False)

    def _load_itemsets(self, itemsets_path: Path) -> pd.DataFrame:
        """Restores frequent itemsets from checkpoint storage."""
        frequent_itemsets: pd.DataFrame = pd.read_parquet(itemsets_path)
        frequent_itemsets['itemsets'] = frequent_itemsets['itemsets'].apply(lambda raw: frozenset(json.loads(raw)))
        return frequent_itemsets

    def _save_rules(self, contrast_df: pd.DataFrame, rules_path: Path) -> None:
        """Persists targeted rules using JSON-serializable list columns."""
        serializable_df: pd.DataFrame = contrast_df.copy()
        serializable_df['antecedents'] = serializable_df['antecedents'].apply(lambda itemset: json.dumps(sorted(itemset)))
        serializable_df['consequents'] = serializable_df['consequents'].apply(lambda itemset: json.dumps(sorted(itemset)))
        serializable_df.to_parquet(rules_path, index=False)

    def _load_rules(self, rules_path: Path) -> pd.DataFrame:
        """Restores targeted rules from checkpoint storage."""
        contrast_df: pd.DataFrame = pd.read_parquet(rules_path)
        contrast_df['antecedents'] = contrast_df['antecedents'].apply(lambda raw: frozenset(json.loads(raw)))
        contrast_df['consequents'] = contrast_df['consequents'].apply(lambda raw: frozenset(json.loads(raw)))
        return contrast_df

    def _write_json(self, output_path: Path, payload: Dict[str, Any]) -> None:
        """Writes structured metadata files for checkpoint inspection."""
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding='utf-8')

    @staticmethod
    def _stringify_itemset(itemset: Iterable[str]) -> str:
        """Converts a rule itemset into stable human-readable text."""
        return ', '.join(sorted(itemset))
