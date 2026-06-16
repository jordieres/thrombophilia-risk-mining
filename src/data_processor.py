"""Shared preprocessing utilities for thrombophilia datasets.

The :class:`ClinicalDataProcessor` centralizes the input/output responsibilities
of the project: loading the raw tabular data, normalizing known sentinel values,
and producing a cleaned dataset that downstream experiments can consume.
"""

from __future__ import annotations

from typing import List, Optional
import pandas as pd
import numpy as np


class ClinicalDataProcessor:
    """Manages high-performance data ingestion and strategic preprocessing pipelines.

    This class provides robust handlers for multi-format file systems, allowing seamless
    transitions between compressed Parquet and standard Excel spreadsheets while establishing
    defensive imputation layers to handle clinical missingness metrics cleanly.
    """

    def __init__(self, file_path: str) -> None:
        """Initializes the data processor with a targeted local disk file path.

        Args:
            file_path (str): The absolute or relative path to the target data file.
        """
        self.file_path: str = file_path
        self.raw_data: Optional[pd.DataFrame] = None
        self.processed_data: Optional[pd.DataFrame] = None

    def load_data(self) -> pd.DataFrame:
        """Loads raw clinical data matrices supporting multi-format files automatically.

        Returns:
            pd.DataFrame: The loaded raw pandas DataFrame matrix.

        Raises:
            ValueError: If the input file extension does not match supported formats.
        """
        if self.file_path.endswith('.parquet') or self.file_path.endswith('.pq'):
            self.raw_data = pd.read_parquet(self.file_path, engine='pyarrow')
        elif self.file_path.endswith('.xlsx') or self.file_path.endswith('.xls'):
            self.raw_data = pd.read_excel(self.file_path)
        elif self.file_path.endswith('.csv'):
            self.raw_data = pd.read_csv(self.file_path)
        else:
            raise ValueError(f"Unsupported file format extension specified: {self.file_path}")
        return self.raw_data

    def transform_pipeline(self) -> pd.DataFrame:
        """Executes the categorical curation and clinical features aggregation sequence.

        This method normalizes vital continuous distributions, maps laboratory markers,
        and ensures missing attributes are classified as non-present securely.

        Returns:
            pd.DataFrame: The processed, analytical clinical dataframe.
        """
        if self.raw_data is None:
            self.load_data()

        df: pd.DataFrame = self.raw_data.copy()

        # Some parquet exports encode missing integer values as int64 minimum sentinel.
        sentinel_int64: int = np.iinfo(np.int64).min
        numeric_cols: List[str] = df.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_cols:
            df[numeric_cols] = df[numeric_cols].replace(sentinel_int64, np.nan)

        # Clinical discrete binning matching initial processing protocols
        if 'hemoglobina' in df.columns:
            df['hemoglobina_cat'] = np.where(df['hemoglobina'] >= 12, 'NormalHemo', 'LowHemo')
        if 'plaquetas' in df.columns:
            df['plaquetas_cat'] = pd.cut(df['plaquetas'], bins=[0, 140, 400, 1000], labels=['LowPlat', 'NormalPlat', 'HighPlat'])

        # Standardize gender mapping via official categorical rename API to prevent deprecation warnings
        if 'sexo' in df.columns:
            if isinstance(df['sexo'].dtype, pd.CategoricalDtype):
                mapping = {cat: ('Male' if cat == 'Hombre' else 'Female' if cat == 'Mujer' else cat) for cat in df['sexo'].cat.categories}
                df['sexo'] = df['sexo'].cat.rename_categories(mapping)
            else:
                df['sexo'] = df['sexo'].astype(str).replace({'Hombre': 'Male', 'Mujer': 'Female'})

        # Defensive missingness imputation checking for formal CategoricalDtype constraints dynamically
        history_cols: List[str] = [col for col in df.columns if col.startswith('fr_') or col.startswith('sin_') or col.startswith('ant_')]
        for col in history_cols:
            if isinstance(df[col].dtype, pd.CategoricalDtype):
                if 'No' not in df[col].cat.categories:
                    df[col] = df[col].cat.add_categories(['No'])
                df[col] = df[col].fillna('No')
            else:
                df[col] = df[col].fillna('No').astype(str)

        # Homogenize all remaining text and object features to prevent mixed float and string types in scikit-learn
        object_cols: List[str] = df.select_dtypes(include=['object']).columns.tolist()
        for col in object_cols:
            df[col] = df[col].fillna('Missing').astype(str)

        self.processed_data = df
        return self.processed_data
