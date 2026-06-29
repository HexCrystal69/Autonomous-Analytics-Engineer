import uuid
import pandas as pd
from typing import Optional
from sqlalchemy.orm import Session
from src.models.catalog import DatasetCatalog, ColumnCatalog
from src.models.dataset import DatasetVersion

class CatalogEngine:
    @staticmethod
    def profile_semantic_metadata(
        db: Session,
        dataset_version_id: uuid.UUID,
        owner: Optional[str] = "Admin"
    ) -> DatasetCatalog:
        """
        Infers semantic types (PII, Financial, Geography, etc.) and PII classifications
        for all columns in a dataset version. Persists the catalog and column records.
        """
        version = db.query(DatasetVersion).filter(DatasetVersion.id == dataset_version_id).first()
        if not version:
            raise ValueError("Dataset version not found")

        df = pd.read_csv(version.file_path) if version.mime_type == "text/csv" else pd.read_excel(version.file_path)

        # Inferred sensitivity level
        sensitivity = "PUBLIC"

        # Check existing catalog for the dataset
        catalog = db.query(DatasetCatalog).filter(DatasetCatalog.dataset_id == version.dataset_id).first()
        if catalog:
            # Re-profile columns by deleting old ones
            db.query(ColumnCatalog).filter(ColumnCatalog.dataset_catalog_id == catalog.id).delete()
        else:
            catalog = DatasetCatalog(
                dataset_id=version.dataset_id,
                data_owner=owner,
                sensitivity_level=sensitivity
            )
            db.add(catalog)
            db.commit()
            db.refresh(catalog)

        has_pii = False

        for col_name in df.columns:
            col_lower = col_name.lower()
            semantic_type = "QUANTITY"
            pii_class = "NONE"
            meaning = f"Column containing raw {col_name} values."

            if "id" in col_lower:
                semantic_type = "IDENTIFIER"
                meaning = "Unique database identifier or foreign reference key."
            elif "email" in col_lower:
                semantic_type = "PII"
                pii_class = "EMAIL"
                has_pii = True
                meaning = "Personally identifiable email address contact field."
            elif "phone" in col_lower or "mobile" in col_lower:
                semantic_type = "PII"
                pii_class = "PHONE"
                has_pii = True
                meaning = "Personally identifiable telephone contact field."
            elif "name" in col_lower:
                semantic_type = "PII"
                pii_class = "NAME"
                has_pii = True
                meaning = "Personally identifiable name descriptor."
            elif "address" in col_lower:
                semantic_type = "PII"
                pii_class = "ADDRESS"
                has_pii = True
                meaning = "Personally identifiable postal street address."
            elif "ip" in col_lower:
                semantic_type = "PII"
                pii_class = "IP"
                has_pii = True
                meaning = "Network server Internet Protocol address."
            elif any(k in col_lower for k in ["revenue", "amount", "price", "sales", "cost", "salary"]):
                semantic_type = "FINANCIAL"
                meaning = "Corporate financial ledger metric currency value."
            elif any(k in col_lower for k in ["country", "city", "state", "zip", "region", "postal"]):
                semantic_type = "GEOGRAPHY"
                meaning = "Geographical territorial location metadata."
            elif any(k in col_lower for k in ["date", "time", "created", "updated", "timestamp"]):
                semantic_type = "TEMPORAL"
                meaning = "Temporal transaction audit log datetime marker."

            col_record = ColumnCatalog(
                dataset_catalog_id=catalog.id,
                column_name=col_name,
                inferred_semantic_type=semantic_type,
                pii_classification=pii_class,
                business_meaning=meaning
            )
            db.add(col_record)

        # Update overall sensitivity if PII columns exist
        if has_pii:
            catalog.sensitivity_level = "CONFIDENTIAL"

        db.commit()
        db.refresh(catalog)
        return catalog
