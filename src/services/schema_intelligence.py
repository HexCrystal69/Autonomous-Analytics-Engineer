import hashlib
import json
import pandas as pd
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.models.dataset import DatasetVersion
from src.models.schema_evolution import SchemaVersion, SchemaChange

class SchemaIntelligence:
    @staticmethod
    def compute_schema_hash(columns_meta: Dict[str, str]) -> str:
        """Generates a stable MD5 hash representing column names and datatypes."""
        serialized = json.dumps(columns_meta, sort_keys=True)
        return hashlib.md5(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def analyze_and_persist(
        cls,
        db: Session,
        dataset_version_id: uuid.UUID
    ) -> SchemaVersion:
        """
        Extracts current schema from version file, checks for drift/changes
        compared to the previous version, and persists version & change records.
        """
        version = db.query(DatasetVersion).filter(DatasetVersion.id == dataset_version_id).first()
        if not version:
            raise ValueError(f"Version {dataset_version_id} not found")

        # Load DataFrame schema
        df = pd.read_csv(version.file_path) if version.mime_type == "text/csv" else pd.read_excel(version.file_path)
        
        # Build schema metadata
        columns_meta = {}
        for col in df.columns:
            columns_meta[col] = str(df[col].dtype)

        schema_hash = cls.compute_schema_hash(columns_meta)

        # Save Schema Version
        schema_version = SchemaVersion(
            dataset_version_id=dataset_version_id,
            schema_hash=schema_hash,
            columns_metadata=columns_meta
        )
        db.add(schema_version)
        db.commit()
        db.refresh(schema_version)

        # Retrieve previous version's schema for drift analysis
        prev_version = db.query(DatasetVersion)\
            .filter(DatasetVersion.dataset_id == version.dataset_id, DatasetVersion.version_number < version.version_number)\
            .order_by(DatasetVersion.version_number.desc())\
            .first()

        if prev_version:
            prev_schema = db.query(SchemaVersion).filter(SchemaVersion.dataset_version_id == prev_version.id).first()
            if prev_schema:
                prev_meta = prev_schema.columns_metadata
                
                # Check for changes
                # 1. Added columns
                for col, dtype in columns_meta.items():
                    if col not in prev_meta:
                        db.add(SchemaChange(
                            schema_version_id=schema_version.id,
                            column_name=col,
                            change_type="ADDED",
                            old_value=None,
                            new_value=dtype,
                            is_breaking=False
                        ))
                
                # 2. Removed columns & type changes
                for col, dtype in prev_meta.items():
                    if col not in columns_meta:
                        db.add(SchemaChange(
                            schema_version_id=schema_version.id,
                            column_name=col,
                            change_type="REMOVED",
                            old_value=dtype,
                            new_value=None,
                            is_breaking=True # Removing a column is a breaking change!
                        ))
                    else:
                        new_dtype = columns_meta[col]
                        if dtype != new_dtype:
                            db.add(SchemaChange(
                                schema_version_id=schema_version.id,
                                column_name=col,
                                change_type="TYPE_CHANGE",
                                old_value=dtype,
                                new_value=new_dtype,
                                is_breaking=True # Datatype conversion can break consumer scripts
                            ))

                db.commit()

        return schema_version
