import re
import pandas as pd
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.models.dataset import DatasetVersion
from src.services.profiling import ProfilingEngine

class QualityEngine:
    @staticmethod
    def validate(
        df: pd.DataFrame,
        rules: List[Any],
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Validates the dataset DataFrame against a list of DataQualityRule models.
        Returns a list of violations (each containing rule_id, severity, column_name, actual_value, expected_value, message).
        """
        violations = []
        row_count = len(df)

        for rule in rules:
            if not rule.enabled:
                continue

            # Parse rule name & definition
            rule_type = rule.rule_type.upper()
            threshold = rule.threshold
            severity = "low"
            # Extract severity from rule name or assign defaults
            if "CRITICAL" in rule.rule_name.upper():
                severity = "critical"
            elif "HIGH" in rule.rule_name.upper():
                severity = "high"
            elif "MEDIUM" in rule.rule_name.upper():
                severity = "medium"

            # 1. Null Percentage check
            if rule_type == "NULL_PERCENT":
                if row_count > 0:
                    null_count = int(df.isnull().sum().sum())
                    total_cells = row_count * len(df.columns)
                    actual_pct = (null_count / total_cells) * 100
                else:
                    actual_pct = 0.0

                if actual_pct > threshold:
                    violations.append({
                        "rule_id": rule.id,
                        "severity": severity,
                        "column_name": None,
                        "actual_value": actual_pct,
                        "expected_value": threshold,
                        "message": f"Overall null percent {actual_pct:.2f}% exceeds threshold {threshold:.2f}%"
                    })

            # 2. Duplicate Percentage check
            elif rule_type == "DUPLICATE_PERCENT":
                if row_count > 0:
                    dup_count = int(df.duplicated().sum())
                    actual_pct = (dup_count / row_count) * 100
                else:
                    actual_pct = 0.0

                if actual_pct > threshold:
                    violations.append({
                        "rule_id": rule.id,
                        "severity": severity,
                        "column_name": None,
                        "actual_value": actual_pct,
                        "expected_value": threshold,
                        "message": f"Duplicate rows percent {actual_pct:.2f}% exceeds threshold {threshold:.2f}%"
                    })

            # 3. Column Specific Null Percentage check
            elif rule_type.startswith("COLUMN_NULL_PERCENT:"):
                col = rule.rule_type.split(":", 1)[1]
                if col in df.columns:
                    null_count = int(df[col].isnull().sum())
                    actual_pct = (null_count / row_count) * 100 if row_count > 0 else 0.0
                    if actual_pct > threshold:
                        violations.append({
                            "rule_id": rule.id,
                            "severity": severity,
                            "column_name": col,
                            "actual_value": actual_pct,
                            "expected_value": threshold,
                            "message": f"Column '{col}' null percent {actual_pct:.2f}% exceeds threshold {threshold:.2f}%"
                        })
                else:
                    violations.append({
                        "rule_id": rule.id,
                        "severity": severity,
                        "column_name": col,
                        "actual_value": None,
                        "expected_value": None,
                        "message": f"Column '{col}' not found in dataset"
                    })

            # 4. Range Validation
            elif rule_type.startswith("COLUMN_MIN:"):
                col = rule.rule_type.split(":", 1)[1]
                if col in df.columns:
                    col_min = df[col].min()
                    # Handle nan
                    if pd.notnull(col_min) and col_min < threshold:
                        violations.append({
                            "rule_id": rule.id,
                            "severity": severity,
                            "column_name": col,
                            "actual_value": float(col_min),
                            "expected_value": threshold,
                            "message": f"Column '{col}' minimum {col_min} is below threshold {threshold}"
                        })
                else:
                    violations.append({
                        "rule_id": rule.id,
                        "severity": severity,
                        "column_name": col,
                        "actual_value": None,
                        "expected_value": None,
                        "message": f"Column '{col}' not found"
                    })

            elif rule_type.startswith("COLUMN_MAX:"):
                col = rule.rule_type.split(":", 1)[1]
                if col in df.columns:
                    col_max = df[col].max()
                    if pd.notnull(col_max) and col_max > threshold:
                        violations.append({
                            "rule_id": rule.id,
                            "severity": severity,
                            "column_name": col,
                            "actual_value": float(col_max),
                            "expected_value": threshold,
                            "message": f"Column '{col}' maximum {col_max} exceeds threshold {threshold}"
                        })
                else:
                    violations.append({
                        "rule_id": rule.id,
                        "severity": severity,
                        "column_name": col,
                        "actual_value": None,
                        "expected_value": None,
                        "message": f"Column '{col}' not found"
                    })

            # 5. Regex Validation
            elif rule_type.startswith("COLUMN_REGEX:"):
                parts = rule.rule_type.split(":", 2)
                col = parts[1]
                # Default regex mapping or use parameter
                pattern_str = parts[2] if len(parts) > 2 else ""
                
                # Preset patterns
                if pattern_str.upper() == "EMAIL":
                    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
                elif pattern_str.upper() == "PHONE":
                    pattern = r"^\+?[1-9]\d{1,14}$" # E.164 phone format
                elif pattern_str.upper() == "ZIPCODE":
                    pattern = r"^\d{5}(-\d{4})?$"
                else:
                    pattern = pattern_str

                if col in df.columns:
                    # Validate all non-null values
                    non_nulls = df[col].dropna().astype(str)
                    failures = 0
                    regex_compiled = re.compile(pattern)
                    for val in non_nulls:
                        if not regex_compiled.match(val):
                            failures += 1
                    
                    fail_pct = (failures / len(non_nulls) * 100) if len(non_nulls) > 0 else 0.0
                    # Threshold is max allowed failure percentage (e.g. threshold = 0.0 means 0% failures allowed)
                    if fail_pct > threshold:
                        violations.append({
                            "rule_id": rule.id,
                            "severity": severity,
                            "column_name": col,
                            "actual_value": fail_pct,
                            "expected_value": threshold,
                            "message": f"Column '{col}' regex mismatch rate {fail_pct:.2f}% exceeds threshold {threshold:.2f}%"
                        })
                else:
                    violations.append({
                        "rule_id": rule.id,
                        "severity": severity,
                        "column_name": col,
                        "actual_value": None,
                        "expected_value": None,
                        "message": f"Column '{col}' not found"
                    })

            # 6. Uniqueness Validation
            elif rule_type.startswith("COLUMN_UNIQUE:"):
                col = rule.rule_type.split(":", 1)[1]
                if col in df.columns:
                    non_nulls = df[col].dropna()
                    dup_count = len(non_nulls) - non_nulls.nunique()
                    dup_pct = (dup_count / len(non_nulls) * 100) if len(non_nulls) > 0 else 0.0
                    
                    if dup_pct > threshold:
                        violations.append({
                            "rule_id": rule.id,
                            "severity": severity,
                            "column_name": col,
                            "actual_value": dup_pct,
                            "expected_value": threshold,
                            "message": f"Column '{col}' uniqueness violation rate {dup_pct:.2f}% exceeds threshold {threshold:.2f}%"
                        })
                else:
                    violations.append({
                        "rule_id": rule.id,
                        "severity": severity,
                        "column_name": col,
                        "actual_value": None,
                        "expected_value": None,
                        "message": f"Column '{col}' not found"
                    })

            # 7. Referential Integrity check (requires db)
            elif rule_type.startswith("REFERENTIAL:"):
                # rule_type format: REFERENTIAL:col_name->target_version_uuid:target_col_name
                try:
                    meta_part = rule.rule_type.split(":", 1)[1]
                    col, target_part = meta_part.split("->", 1)
                    target_ver_str, target_col = target_part.split(":", 1)
                    target_ver_id = uuid.UUID(target_ver_str)
                except Exception:
                    violations.append({
                        "rule_id": rule.id,
                        "severity": severity,
                        "column_name": None,
                        "actual_value": None,
                        "expected_value": None,
                        "message": f"Invalid referential rule definition: {rule.rule_type}"
                    })
                    continue

                if db is None:
                    # Skip or fail if DB session not provided
                    continue

                target_ver = db.query(DatasetVersion).filter(DatasetVersion.id == target_ver_id).first()
                if not target_ver:
                    violations.append({
                        "rule_id": rule.id,
                        "severity": severity,
                        "column_name": col,
                        "actual_value": None,
                        "expected_value": None,
                        "message": f"Referential validation target version {target_ver_id} not found"
                    })
                    continue

                if col in df.columns:
                    # Read target dataset version
                    try:
                        target_df = ProfilingEngine.load_dataset(target_ver.file_path, target_ver.mime_type)
                    except Exception as e:
                        violations.append({
                            "rule_id": rule.id,
                            "severity": severity,
                            "column_name": col,
                            "actual_value": None,
                            "expected_value": None,
                            "message": f"Failed to load target dataset for referential integrity: {str(e)}"
                        })
                        continue

                    if target_col in target_df.columns:
                        source_vals = set(df[col].dropna().unique())
                        target_vals = set(target_df[target_col].dropna().unique())
                        
                        missing_keys = source_vals - target_vals
                        missing_pct = (len(missing_keys) / len(source_vals) * 100) if len(source_vals) > 0 else 0.0

                        if missing_pct > threshold:
                            violations.append({
                                "rule_id": rule.id,
                                "severity": severity,
                                "column_name": col,
                                "actual_value": missing_pct,
                                "expected_value": threshold,
                                "message": f"Referential integrity mismatch rate {missing_pct:.2f}% exceeds threshold {threshold:.2f}%"
                            })
                    else:
                        violations.append({
                            "rule_id": rule.id,
                            "severity": severity,
                            "column_name": col,
                            "actual_value": None,
                            "expected_value": None,
                            "message": f"Referential validation target column '{target_col}' not found"
                        })
                else:
                    violations.append({
                        "rule_id": rule.id,
                        "severity": severity,
                        "column_name": col,
                        "actual_value": None,
                        "expected_value": None,
                        "message": f"Column '{col}' not found"
                    })

        return violations
