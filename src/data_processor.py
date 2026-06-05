"""Shared preprocessing utilities for thrombophilia datasets.

The :class:`ClinicalDataProcessor` centralizes the input/output responsibilities
of the project: loading the raw tabular data, normalizing known sentinel values,
and producing a cleaned dataset that downstream experiments can consume.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd


class ClinicalDataProcessor:
    """Load and preprocess thrombophilia datasets.

    The processor intentionally keeps the transformation pipeline lightweight and
    deterministic so all analytical experiments start from the same curated
    dataframe.

    Attributes:
        file_path: Path to the source tabular dataset.
        raw_data: Dataframe loaded directly from disk before transformations.
        processed_data: Cleaned dataframe produced by :meth:`transform_pipeline`.
    """

    INT64_SENTINEL: Final[int] = int(np.iinfo(np.int64).min)
    HISTORY_PREFIXES: Final[tuple[str, str]] = ("fr_", "sin_")

    def __init__(self, file_path: str) -> None:
        """Store the source path used by the processor.

        Args:
            file_path: Path to an input CSV, Excel, or Parquet file.
        """
        self.file_path: str = file_path
        self.raw_data: pd.DataFrame | None = None
        self.processed_data: pd.DataFrame | None = None

    def load_data(self) -> pd.DataFrame:
        """Load the source dataset from disk.

        Returns:
            Raw dataframe loaded from the configured file path.
        """
        if self.file_path.endswith((".parquet", ".pq")):
            self.raw_data = pd.read_parquet(self.file_path, engine="pyarrow")
        elif self.file_path.endswith((".xlsx", ".xls")):
            self.raw_data = pd.read_excel(self.file_path)
        else:
            self.raw_data = pd.read_csv(self.file_path)
        return self.raw_data

    def transform_pipeline(self) -> pd.DataFrame:
        """Apply the shared preprocessing pipeline.

        Returns:
            Cleaned dataframe ready for consumption by analytical experiments.

        Raises:
            ValueError: If the raw dataset has not been loaded yet.
        """
        if self.raw_data is None:
            raise ValueError("Data must be loaded before the transformation pipeline can run.")

        df = self.raw_data.copy()

        # Replace sentinel values commonly used by integer-backed nullable fields.
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            df[numeric_cols] = df[numeric_cols].replace(self.INT64_SENTINEL, np.nan)

        # Derive categorical summaries used by multiple exploratory experiments.
        if "hemoglobina" in df.columns:
            df["hemoglobina_cat"] = np.where(df["hemoglobina"] >= 12, "NormalHemo", "LowHemo")
        if "plaquetas" in df.columns:
            df["plaquetas_cat"] = pd.cut(
                df["plaquetas"],
                bins=[0, 140, 400, 1000],
                labels=["LowPlat", "NormalPlat", "HighPlat"],
            )

        # Harmonize missing values in boolean-like history flags.
        history_cols = [
            column
            for column in df.columns
            if column.startswith(self.HISTORY_PREFIXES)
        ]
        for column in history_cols:
            series = df[column]
            if isinstance(series.dtype, pd.CategoricalDtype) and "No" not in series.cat.categories:
                series = series.cat.add_categories(["No"])
            df[column] = series.fillna("No")

        self.processed_data = df
        return self.processed_data
