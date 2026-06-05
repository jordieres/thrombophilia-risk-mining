import pandas as pd
import numpy as np

class ClinicalDataProcessor:
    """Responsible for loading, cleaning, and discretizing the national database streams."""

    def __init__(self, file_path):
        """Initializes the processor with the data source path.

        Args:
            file_path (str): Path to the raw Excel, CSV, or Parquet file.
        """
        self.file_path = file_path
        self.raw_data = None
        self.processed_data = None

    def load_data(self):
        """Ingests the clinical records automatically supporting multiple disk formats."""
        if self.file_path.endswith('.parquet') or self.file_path.endswith('.pq'):
            self.raw_data = pd.read_parquet(self.file_path, engine='pyarrow')
        elif self.file_path.endswith('.xlsx') or self.file_path.endswith('.xls'):
            self.raw_data = pd.read_excel(self.file_path)
        else:
            self.raw_data = pd.read_csv(self.file_path)
        return self.raw_data

    def transform_pipeline(self):
        """Executes the complete curation, binarization, and clinical feature aggregation.

        Returns:
            pd.DataFrame: Normalized and cleaned dataset.
        """
        df = self.raw_data.copy()
        
        # Clinical normalization protocols matching initial processing scripts
        if 'hemoglobina' in df.columns:
            df['hemoglobina_cat'] = np.where(df['hemoglobina'] >= 12, 'NormalHemo', 'LowHemo')
        if 'plaquetas' in df.columns:
            df['plaquetas_cat'] = pd.cut(df['plaquetas'], bins=[0, 140, 400, 1000], labels=['LowPlat', 'NormalPlat', 'HighPlat'])
            
        # Imputing missing categorical histories defensively to maintain baseline safety
        history_cols = [col for col in df.columns if col.startswith('fr_') or col.startswith('sin_')]
        for col in history_cols:
            df[col] = df[col].fillna('No')
            
        self.processed_data = df
        return self.processed_data
