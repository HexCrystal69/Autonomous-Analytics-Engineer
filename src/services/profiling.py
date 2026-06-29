import io
import math
import numpy as np
import pandas as pd
from typing import Dict, Any, List

class ProfilingEngine:
    @staticmethod
    def load_dataset(file_path: str, mime_type: str) -> pd.DataFrame:
        """Loads a dataset from the filesystem based on mime_type or file extension."""
        if "excel" in mime_type or "spreadsheetml" in mime_type or file_path.endswith(".xlsx"):
            return pd.read_excel(file_path)
        else:
            # Default to CSV
            return pd.read_csv(file_path)

    @classmethod
    def profile(cls, file_path: str, mime_type: str) -> Dict[str, Any]:
        """Runs the profile calculation on the dataset and returns results."""
        df = cls.load_dataset(file_path, mime_type)
        
        row_count = len(df)
        column_count = len(df.columns)
        
        # Duplicate rows
        duplicate_rows_count = int(df.duplicated().sum())
        duplicate_rows_percent = float((duplicate_rows_count / row_count) * 100) if row_count > 0 else 0.0

        # Overall missing
        total_cells = row_count * column_count
        missing_cells_count = int(df.isnull().sum().sum())
        missing_cells_percent = float((missing_cells_count / total_cells) * 100) if total_cells > 0 else 0.0

        summary_metrics = {
            "row_count": row_count,
            "column_count": column_count,
            "duplicate_rows_count": duplicate_rows_count,
            "duplicate_rows_percent": duplicate_rows_percent,
            "total_cells": total_cells,
            "missing_cells_count": missing_cells_count,
            "missing_cells_percent": missing_cells_percent,
        }

        columns_metadata = {}

        for col_name in df.columns:
            col_data = df[col_name]
            dtype_str = str(col_data.dtype)
            
            missing_count = int(col_data.isnull().sum())
            missing_percent = float((missing_count / row_count) * 100) if row_count > 0 else 0.0
            
            unique_count = int(col_data.nunique(dropna=True))
            unique_percent = float((unique_count / row_count) * 100) if row_count > 0 else 0.0
            
            col_meta: Dict[str, Any] = {
                "name": col_name,
                "data_type": dtype_str,
                "missing_count": missing_count,
                "missing_percent": missing_percent,
                "unique_count": unique_count,
                "unique_percent": unique_percent,
                "cardinality": unique_count,
            }

            # Check if column is numeric
            if np.issubdtype(col_data.dtype, np.number):
                clean_data = col_data.dropna()
                if not clean_data.empty:
                    q1 = float(clean_data.quantile(0.25))
                    q3 = float(clean_data.quantile(0.75))
                    iqr = q3 - q1
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    outliers = clean_data[(clean_data < lower_bound) | (clean_data > upper_bound)]
                    outlier_count = int(len(outliers))

                    col_meta.update({
                        "is_numeric": True,
                        "min": float(clean_data.min()) if not math.isnan(clean_data.min()) else None,
                        "max": float(clean_data.max()) if not math.isnan(clean_data.max()) else None,
                        "mean": float(clean_data.mean()) if not math.isnan(clean_data.mean()) else None,
                        "median": float(clean_data.median()) if not math.isnan(clean_data.median()) else None,
                        "std": float(clean_data.std()) if not (math.isnan(clean_data.std()) or len(clean_data) < 2) else 0.0,
                        "p25": q1,
                        "p75": q3,
                        "outlier_count": outlier_count,
                    })
                else:
                    col_meta.update({
                        "is_numeric": True,
                        "min": None,
                        "max": None,
                        "mean": None,
                        "median": None,
                        "std": None,
                        "p25": None,
                        "p75": None,
                        "outlier_count": 0,
                    })
            else:
                # Categorical column
                col_meta["is_numeric"] = False
                # Top values
                value_counts = col_data.value_counts(dropna=True).head(10)
                top_values = []
                freq_dist = {}
                for val, count in value_counts.items():
                    val_str = str(val)
                    top_values.append(val_str)
                    freq_dist[val_str] = int(count)
                
                col_meta.update({
                    "top_values": top_values,
                    "frequency_distribution": freq_dist,
                })
            
            columns_metadata[col_name] = col_meta

        return {
            "summary_metrics": summary_metrics,
            "columns_metadata": columns_metadata,
        }

    @staticmethod
    def validate_rules(profile_result: Dict[str, Any], rules: List[Any]) -> Dict[str, Any]:
        """Validates computed profile metrics against a list of DataQualityRule objects."""
        summary = profile_result["summary_metrics"]
        cols = profile_result["columns_metadata"]
        
        validations = []
        all_passed = True

        for rule in rules:
            if not rule.enabled:
                continue
            
            passed = True
            error_msg = ""
            actual_value = None

            # Standard rules validation
            if rule.rule_type == "NULL_PERCENT":
                # Expect threshold to be maximum allowed missing percentage
                actual_value = summary["missing_cells_percent"]
                if actual_value > rule.threshold:
                    passed = False
                    error_msg = f"Overall null percent {actual_value:.2f}% exceeds threshold {rule.threshold:.2f}%"
            
            elif rule.rule_type == "DUPLICATE_PERCENT":
                actual_value = summary["duplicate_rows_percent"]
                if actual_value > rule.threshold:
                    passed = False
                    error_msg = f"Duplicate rows percent {actual_value:.2f}% exceeds threshold {rule.threshold:.2f}%"

            elif rule.rule_type.startswith("COLUMN_NULL_PERCENT:"):
                col_name = rule.rule_type.split(":", 1)[1]
                if col_name in cols:
                    actual_value = cols[col_name]["missing_percent"]
                    if actual_value > rule.threshold:
                        passed = False
                        error_msg = f"Column '{col_name}' null percent {actual_value:.2f}% exceeds threshold {rule.threshold:.2f}%"
                else:
                    passed = False
                    error_msg = f"Column '{col_name}' not found in dataset"
            
            elif rule.rule_type.startswith("COLUMN_MIN:"):
                col_name = rule.rule_type.split(":", 1)[1]
                if col_name in cols:
                    col_info = cols[col_name]
                    if col_info.get("is_numeric"):
                        actual_value = col_info.get("min")
                        if actual_value is not None and actual_value < rule.threshold:
                            passed = False
                            error_msg = f"Column '{col_name}' min value {actual_value} is below threshold {rule.threshold}"
                    else:
                        passed = False
                        error_msg = f"Column '{col_name}' is not numeric"
                else:
                    passed = False
                    error_msg = f"Column '{col_name}' not found in dataset"

            elif rule.rule_type.startswith("COLUMN_MAX:"):
                col_name = rule.rule_type.split(":", 1)[1]
                if col_name in cols:
                    col_info = cols[col_name]
                    if col_info.get("is_numeric"):
                        actual_value = col_info.get("max")
                        if actual_value is not None and actual_value > rule.threshold:
                            passed = False
                            error_msg = f"Column '{col_name}' max value {actual_value} is above threshold {rule.threshold}"
                    else:
                        passed = False
                        error_msg = f"Column '{col_name}' is not numeric"
                else:
                    passed = False
                    error_msg = f"Column '{col_name}' not found in dataset"

            else:
                passed = False
                error_msg = f"Unsupported rule type: {rule.rule_type}"

            if not passed:
                all_passed = False

            validations.append({
                "rule_id": str(rule.id),
                "rule_name": rule.rule_name,
                "rule_type": rule.rule_type,
                "threshold": rule.threshold,
                "actual_value": actual_value,
                "passed": passed,
                "error_message": error_msg,
            })

        return {
            "all_passed": all_passed,
            "validations": validations
        }
