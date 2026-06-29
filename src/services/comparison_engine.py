import numpy as np
import pandas as pd
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from src.models.dataset import DatasetVersion
from src.models.comparison import DatasetComparison, ColumnComparison
from src.models.profile import DatasetProfile
from src.models.reliability import ValidationReport
from src.services.profiling import ProfilingEngine

class ComparisonEngine:
    @staticmethod
    def compare_versions(
        db: Session,
        source_version_id: uuid.UUID,
        target_version_id: uuid.UUID
    ) -> DatasetComparison:
        """
        Compares two dataset versions and returns the persisted DatasetComparison model.
        Calculates row/column deltas, health/quality/anomaly/drift deltas, and column-level shifts.
        """
        source = db.query(DatasetVersion).filter(DatasetVersion.id == source_version_id).first()
        target = db.query(DatasetVersion).filter(DatasetVersion.id == target_version_id).first()

        if not source or not target:
            raise ValueError("Source or target dataset version not found")

        # Load datasets
        df_source = ProfilingEngine.load_dataset(source.file_path, source.mime_type)
        df_target = ProfilingEngine.load_dataset(target.file_path, target.mime_type)

        # Row/col deltas
        row_delta = len(df_target) - len(df_source)
        col_delta = len(df_target.columns) - len(df_source.columns)

        # Fetch validation reports if exist
        rep_source = db.query(ValidationReport).filter(ValidationReport.dataset_version_id == source_version_id).first()
        rep_target = db.query(ValidationReport).filter(ValidationReport.dataset_version_id == target_version_id).first()

        health_delta = (rep_target.health_score - rep_source.health_score) if (rep_source and rep_target) else 0.0
        quality_delta = (rep_target.quality_score - rep_source.quality_score) if (rep_source and rep_target) else 0.0
        anomaly_delta = (rep_target.anomaly_score - rep_source.anomaly_score) if (rep_source and rep_target) else 0.0
        drift_delta = (rep_target.drift_score - rep_source.drift_score) if (rep_source and rep_target) else 0.0

        # Save main comparison record
        comparison = DatasetComparison(
            source_version_id=source_version_id,
            target_version_id=target_version_id,
            row_delta=row_delta,
            column_delta=col_delta,
            health_delta=health_delta,
            quality_delta=quality_delta,
            anomaly_delta=anomaly_delta,
            drift_delta=drift_delta
        )
        db.add(comparison)
        db.commit()
        db.refresh(comparison)

        # Ingest profiles
        prof_source = db.query(DatasetProfile).filter(DatasetProfile.dataset_version_id == source_version_id).first()
        prof_target = db.query(DatasetProfile).filter(DatasetProfile.dataset_version_id == target_version_id).first()

        # Compute column-level deltas
        for col_name in df_target.columns:
            if col_name not in df_source.columns:
                continue

            # Default deltas
            null_delta = 0.0
            mean_delta = 0.0
            median_delta = 0.0
            std_delta = 0.0
            cardinality_delta = 0

            # Pull stats from profile metadata if available, otherwise compute directly
            if prof_source and prof_target:
                src_cols = prof_source.columns_metadata
                targ_cols = prof_target.columns_metadata
                
                if col_name in src_cols and col_name in targ_cols:
                    src_col = src_cols[col_name]
                    targ_col = targ_cols[col_name]

                    null_delta = targ_col.get("missing_percent", 0.0) - src_col.get("missing_percent", 0.0)
                    cardinality_delta = targ_col.get("cardinality", 0) - src_col.get("cardinality", 0)

                    if src_col.get("is_numeric") and targ_col.get("is_numeric"):
                        mean_delta = targ_col.get("mean", 0.0) - src_col.get("mean", 0.0)
                        median_delta = targ_col.get("median", 0.0) - src_col.get("median", 0.0)
                        std_delta = targ_col.get("std", 0.0) - src_col.get("std", 0.0)
            else:
                # Fallback to direct computation
                s_col = df_source[col_name]
                t_col = df_target[col_name]

                null_delta = (t_col.isnull().sum() / len(df_target) * 100) - (s_col.isnull().sum() / len(df_source) * 100)
                cardinality_delta = int(t_col.nunique()) - int(s_col.nunique())

                if np.issubdtype(s_col.dtype, np.number) and np.issubdtype(t_col.dtype, np.number):
                    mean_delta = float(t_col.mean() - s_col.mean()) if pd.notnull(t_col.mean()) and pd.notnull(s_col.mean()) else 0.0
                    median_delta = float(t_col.median() - s_col.median()) if pd.notnull(t_col.median()) and pd.notnull(s_col.median()) else 0.0
                    std_delta = float(t_col.std() - s_col.std()) if pd.notnull(t_col.std()) and pd.notnull(s_col.std()) else 0.0

            col_comparison = ColumnComparison(
                comparison_id=comparison.id,
                column_name=col_name,
                null_delta=float(null_delta),
                mean_delta=float(mean_delta),
                median_delta=float(median_delta),
                std_delta=float(std_delta),
                cardinality_delta=int(cardinality_delta)
            )
            db.add(col_comparison)

        db.commit()
        return comparison
