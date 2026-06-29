import numpy as np
import pandas as pd
from typing import List, Dict, Any
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

class AnomalyEngine:
    @staticmethod
    def detect_zscore(df: pd.DataFrame, threshold: float = 3.0) -> List[Dict[str, Any]]:
        """Detect anomalies using Z-score method for numerical columns."""
        anomalies = []
        for col in df.columns:
            col_data = df[col]
            if np.issubdtype(col_data.dtype, np.number):
                clean_data = col_data.dropna()
                if len(clean_data) > 2:
                    mean = clean_data.mean()
                    std = clean_data.std()
                    if std > 0:
                        for idx, val in col_data.items():
                            if pd.notnull(val):
                                z = abs(val - mean) / std
                                if z > threshold:
                                    anomalies.append({
                                        "column_name": col,
                                        "row_index": int(idx),
                                        "score": float(z),
                                        "anomaly_type": "Z_SCORE",
                                        "details_json": {"value": float(val), "mean": float(mean), "std": float(std)}
                                    })
        return anomalies

    @staticmethod
    def detect_iqr(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect anomalies using IQR method for numerical columns."""
        anomalies = []
        for col in df.columns:
            col_data = df[col]
            if np.issubdtype(col_data.dtype, np.number):
                clean_data = col_data.dropna()
                if not clean_data.empty:
                    q1 = clean_data.quantile(0.25)
                    q3 = clean_data.quantile(0.75)
                    iqr = q3 - q1
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    for idx, val in col_data.items():
                        if pd.notnull(val):
                            if val < lower_bound or val > upper_bound:
                                anomalies.append({
                                    "column_name": col,
                                    "row_index": int(idx),
                                    "score": float(abs(val - clean_data.median()) / (iqr if iqr > 0 else 1.0)),
                                    "anomaly_type": "IQR",
                                    "details_json": {"value": float(val), "lower_bound": float(lower_bound), "upper_bound": float(upper_bound)}
                                })
        return anomalies

    @staticmethod
    def detect_isolation_forest(df: pd.DataFrame, contamination: float = 0.05) -> List[Dict[str, Any]]:
        """Detect anomalies using scikit-learn's Isolation Forest."""
        anomalies = []
        # Get numerical columns
        numeric_cols = [col for col in df.columns if np.issubdtype(df[col].dtype, np.number)]
        if not numeric_cols or len(df) < 5:
            return anomalies

        # Impute or drop na values for fit
        sub_df = df[numeric_cols].copy()
        # Simple imputation with median
        for col in numeric_cols:
            median = sub_df[col].median()
            sub_df[col] = sub_df[col].fillna(median if pd.notnull(median) else 0.0)

        try:
            model = IsolationForest(contamination=contamination, random_state=42)
            # fit predict: outlier labels: -1, inlier labels: 1
            preds = model.fit_predict(sub_df)
            decision_scores = model.decision_function(sub_df)

            for idx, (pred, score) in enumerate(zip(preds, decision_scores)):
                if pred == -1:
                    # Collect the columns contributing to the anomaly
                    anomalies.append({
                        "column_name": "MULTIVARIATE",
                        "row_index": int(idx),
                        "score": float(-score), # Convert to positive outlier score
                        "anomaly_type": "ISOLATION_FOREST",
                        "details_json": {"values": sub_df.iloc[idx].to_dict(), "raw_score": float(score)}
                    })
        except Exception:
            pass

        return anomalies

    @staticmethod
    def detect_local_outlier_factor(df: pd.DataFrame, contamination: float = 0.05) -> List[Dict[str, Any]]:
        """Detect anomalies using scikit-learn's Local Outlier Factor."""
        anomalies = []
        numeric_cols = [col for col in df.columns if np.issubdtype(df[col].dtype, np.number)]
        if not numeric_cols or len(df) < 5:
            return anomalies

        sub_df = df[numeric_cols].copy()
        for col in numeric_cols:
            median = sub_df[col].median()
            sub_df[col] = sub_df[col].fillna(median if pd.notnull(median) else 0.0)

        try:
            model = LocalOutlierFactor(n_neighbors=min(20, len(df)-1), contamination=contamination)
            preds = model.fit_predict(sub_df)
            negative_outlier_factor = model.negative_outlier_factor_

            for idx, (pred, score) in enumerate(zip(preds, negative_outlier_factor)):
                if pred == -1:
                    anomalies.append({
                        "column_name": "MULTIVARIATE",
                        "row_index": int(idx),
                        "score": float(-score), # Higher score means more anomalous
                        "anomaly_type": "LOCAL_OUTLIER_FACTOR",
                        "details_json": {"values": sub_df.iloc[idx].to_dict(), "lof_score": float(score)}
                    })
        except Exception:
            pass

        return anomalies
