import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from xgboost import XGBClassifier
from sklearn.inspection import permutation_importance
from experiment_base import BaseExperiment

class PermutationImportanceExperiment(BaseExperiment):
    """Study 1: Feature importance isolating secondary lab variables by dropping demographic features."""

    def __init__(self):
        super().__init__("Permutation Importance Without Demographics")

    def run(self, data):
        """Runs a 10-fold cross-validation routine excluding age and sex to isolate hidden predictors."""
        df = data.copy()
        
        # Enforce demographic isolation by removing dominant signals
        excluded_features = ['sexo', 'edad', 'edadC', 'sex']
        features = [col for col in df.columns if col not in excluded_features and col != 'ana_dura']
        
        X = df[features]
        y = np.where(df['ana_dura'] == 'Buscada negativo', 1, 0)
        
        # Identify categorical positions automatically for transformation
        cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
        num_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        
        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_cols),
                ('num', 'passthrough', num_cols)
            ])
        
        X_trans = preprocessor.fit_transform(X)
        feature_names = preprocessor.get_feature_names_out()
        
        skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
        importances = []
        
        # Model training loop utilizing cross-validation for strict sample independence
        for train_idx, test_idx in skf.split(X_trans, y):
            X_train, X_test = X_trans[train_idx], X_trans[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            model = XGBClassifier(n_estimators=100, max_depth=5, random_state=42, eval_metric='logloss')
            model.fit(X_train, y_train)
            
            result = permutation_importance(model, X_test, y_test, n_repeats=5, random_state=42, n_jobs=-1)
            importances.append(result.importances_mean)
            
        mean_importances = np.mean(importances, axis=0)
        results_df = pd.DataFrame({'Feature': feature_names, 'Importance': mean_importances})
        results_df = results_df.sort_values(by='Importance', ascending=False).head(10)
        
        # Generate LaTeX table output
        self.latex_table = results_df.to_latex(index=False, caption="Top Secondary Predictors Isolating Demographics", label="tab:perm_imp")
        
        # Generate interactive Plotly visualization
        self.plotly_figure = px.bar(results_df, x='Importance', y='Feature', orientation='h',
                                    title="Isolated Clinical Feature Importance (Excluding Demographics)")
        self.plotly_figure.update_layout(yaxis={'categoryorder':'total ascending'})
