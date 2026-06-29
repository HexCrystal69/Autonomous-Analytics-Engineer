import uuid
import hashlib
import json
import re
import pandas as pd
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from src.models.contract import DataContract, DataContractRule, ContractVersion, ContractViolation
from src.models.dataset import DatasetVersion
from src.models.catalog import ColumnCatalog, DatasetCatalog
from src.services.profiling import ProfilingEngine

class ContractEngine:
    @staticmethod
    def create_contract(
        db: Session,
        dataset_id: uuid.UUID,
        name: str,
        owner: str,
        description: Optional[str] = None,
        contract_version: str = "1.0.0",
        rules: Optional[List[Dict[str, Any]]] = None
    ) -> DataContract:
        # Check if active contract exists, deprecate it
        existing = db.query(DataContract).filter(
            DataContract.dataset_id == dataset_id,
            DataContract.status == "active"
        ).all()
        for c in existing:
            c.status = "deprecated"

        contract = DataContract(
            dataset_id=dataset_id,
            name=name,
            owner=owner,
            description=description,
            contract_version=contract_version,
            status="active"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        if rules:
            for r in rules:
                rule_record = DataContractRule(
                    contract_id=contract.id,
                    rule_type=r["rule_type"],
                    column_name=r.get("column_name"),
                    expected_value=str(r.get("expected_value")),
                    severity=r.get("severity", "high")
                )
                db.add(rule_record)
            db.commit()
            db.refresh(contract)

        return contract

    @staticmethod
    def add_version(
        db: Session,
        contract_id: uuid.UUID,
        version_str: str,
        schema_columns: List[str]
    ) -> ContractVersion:
        columns_sorted = sorted(schema_columns)
        schema_hash = hashlib.sha256(",".join(columns_sorted).encode()).hexdigest()


        version = ContractVersion(
            contract_id=contract_id,
            version=version_str,
            schema_hash=schema_hash
        )
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def validate_version(
        db: Session,
        dataset_version_id: uuid.UUID,
        contract_id: Optional[uuid.UUID] = None
    ) -> List[ContractViolation]:
        version = db.query(DatasetVersion).filter(DatasetVersion.id == dataset_version_id).first()
        if not version:
            return []

        # Find active contract
        if contract_id:
            contract = db.query(DataContract).filter(DataContract.id == contract_id).first()
        else:
            contract = db.query(DataContract).filter(
                DataContract.dataset_id == version.dataset_id,
                DataContract.status == "active"
            ).first()

        if not contract:
            return []

        violations = []
        try:
            df = pd.read_csv(version.file_path) if version.mime_type == "text/csv" else pd.read_excel(version.file_path)
        except Exception:
            # File missing or unreadable
            return []

        # Load catalog for column types
        catalog = db.query(DatasetCatalog).filter(DatasetCatalog.dataset_id == version.dataset_id).first()
        col_types = {}
        if catalog:
            cols = db.query(ColumnCatalog).filter(ColumnCatalog.dataset_catalog_id == catalog.id).all()
            col_types = {c.column_name: c.semantic_type for c in cols}

        for rule in contract.rules:
            violation_msg = None

            # 1. Column presence check
            if rule.rule_type == "column_exists":
                if rule.column_name not in df.columns:
                    violation_msg = f"Required column '{rule.column_name}' is missing from the schema."

            # 2. Column type check
            elif rule.rule_type == "column_type":
                if rule.column_name in df.columns:
                    actual_sem = col_types.get(rule.column_name)
                    expected = rule.expected_value
                    if actual_sem != expected:
                        violation_msg = f"Column '{rule.column_name}' inferred type '{actual_sem}' does not match expected '{expected}'."

            # 3. Max null percentage check
            elif rule.rule_type == "max_null_pct":
                if rule.column_name in df.columns:
                    null_pct = (df[rule.column_name].isnull().sum() / len(df)) * 100.0
                    threshold = float(rule.expected_value or 0)
                    if null_pct > threshold:
                        violation_msg = f"Column '{rule.column_name}' null percentage {null_pct:.2f}% exceeds threshold of {threshold}%."

            # 4. Uniqueness check
            elif rule.rule_type == "uniqueness":
                if rule.column_name in df.columns:
                    non_nulls = df[rule.column_name].dropna()
                    if len(non_nulls) > 0:
                        uniq_pct = (non_nulls.nunique() / len(non_nulls)) * 100.0
                        threshold = float(rule.expected_value or 100)
                        if uniq_pct < threshold:
                            violation_msg = f"Column '{rule.column_name}' uniqueness ratio {uniq_pct:.2f}% is below expected threshold of {threshold}%."

            # 5. Regex check
            elif rule.rule_type == "regex":
                if rule.column_name in df.columns:
                    pattern = rule.expected_value
                    if pattern:
                        non_nulls = df[rule.column_name].dropna().astype(str)
                        matches = non_nulls.apply(lambda x: bool(re.match(pattern, x)))
                        if not matches.all():
                            fail_count = len(matches) - matches.sum()
                            violation_msg = f"Column '{rule.column_name}' has {fail_count} values that do not match the expected pattern."

            # 6. Range check
            elif rule.rule_type == "range":
                if rule.column_name in df.columns:
                    try:
                        limits = json.loads(rule.expected_value)
                        min_val = limits.get("min")
                        max_val = limits.get("max")
                        series = pd.to_numeric(df[rule.column_name].dropna(), errors="coerce")
                        if min_val is not None and (series < min_val).any():
                            violation_msg = f"Column '{rule.column_name}' has values below minimum limit of {min_val}."
                        elif max_val is not None and (series > max_val).any():
                            violation_msg = f"Column '{rule.column_name}' has values above maximum limit of {max_val}."
                    except Exception:
                        pass

            if violation_msg:
                violation = ContractViolation(
                    contract_rule_id=rule.id,
                    dataset_version_id=dataset_version_id,
                    severity=rule.severity,
                    message=violation_msg
                )
                db.add(violation)
                violations.append(violation)

        if violations:
            db.commit()

        return violations
