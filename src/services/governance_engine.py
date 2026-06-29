import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from src.models.governance import GovernancePolicy, DatasetPolicyMapping, ComplianceSnapshot
from src.models.catalog import DatasetCatalog
from src.models.dataset import DatasetVersion
from src.models.freshness import DatasetFreshnessRecord
from src.models.contract import ContractViolation
from src.models.reliability import ValidationReport

class GovernanceEngine:
    @staticmethod
    def create_policy(
        db: Session,
        name: str,
        category: str,
        description: Optional[str] = None,
        severity: str = "medium"
    ) -> GovernancePolicy:
        policy = GovernancePolicy(
            name=name,
            category=category,
            description=description,
            severity=severity
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
        return policy

    @staticmethod
    def map_policy(
        db: Session,
        dataset_id: uuid.UUID,
        policy_id: uuid.UUID
    ) -> DatasetPolicyMapping:
        mapping = DatasetPolicyMapping(
            dataset_id=dataset_id,
            policy_id=policy_id,
            status="active"
        )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return mapping

    @staticmethod
    def evaluate_compliance(db: Session, dataset_id: uuid.UUID) -> Optional[ComplianceSnapshot]:
        mappings = db.query(DatasetPolicyMapping).filter(
            DatasetPolicyMapping.dataset_id == dataset_id,
            DatasetPolicyMapping.status == "active"
        ).all()

        if not mappings:
            # Create default 100% compliance snapshot if no policies are mapped
            snapshot = ComplianceSnapshot(
                dataset_id=dataset_id,
                compliance_score=100.0,
                failed_policies=[],
                passed_policies=[]
            )
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)
            return snapshot

        passed = []
        failed = []

        # Load metrics needed for rules evaluation
        catalog = db.query(DatasetCatalog).filter(DatasetCatalog.dataset_id == dataset_id).first()
        versions = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version_number.desc()).all()
        latest_ver = versions[0] if versions else None
        
        freshness = db.query(DatasetFreshnessRecord).filter(
            DatasetFreshnessRecord.dataset_id == dataset_id
        ).order_by(DatasetFreshnessRecord.recorded_at.desc()).first()


        report = db.query(ValidationReport).filter(
            ValidationReport.dataset_version_id == latest_ver.id
        ).first() if latest_ver else None

        for m in mappings:
            policy = m.policy
            is_compliant = True

            # 1. PII Compliance: CONFIDENTIAL sensitivity level when PII columns are present
            if policy.category == "PII Compliance":
                if catalog and catalog.sensitivity_level == "PUBLIC":
                    # If PII categories found, it should be CONFIDENTIAL
                    # We look up if any column is marked PII in catalog columns
                    from src.models.catalog import ColumnCatalog
                    pii_cols = db.query(ColumnCatalog).filter(
                        ColumnCatalog.dataset_catalog_id == catalog.id,
                        ColumnCatalog.semantic_type == "PII"
                    ).count()
                    if pii_cols > 0:
                        is_compliant = False

            # 2. Retention Policy: max 5 versions limit
            elif policy.category == "Retention Policy":
                if len(versions) > 5:
                    is_compliant = False

            # 3. Freshness Policy: no "critical" delay records
            elif policy.category == "Freshness Policy":
                if freshness and freshness.status == "critical":
                    is_compliant = False

            # 4. Schema Governance: no active contract violations in latest version
            elif policy.category == "Schema Governance":
                if latest_ver:
                    violations = db.query(ContractViolation).filter(
                        ContractViolation.dataset_version_id == latest_ver.id
                    ).count()
                    if violations > 0:
                        is_compliant = False

            # 5. Quality Standards: health_score >= 80.0
            elif policy.category == "Quality Standards":
                if report and report.health_score < 80.0:
                    is_compliant = False

            if is_compliant:
                passed.append(str(policy.id))
            else:
                failed.append(str(policy.id))

        total = len(mappings)
        score = (len(passed) / total) * 100.0

        snapshot = ComplianceSnapshot(
            dataset_id=dataset_id,
            compliance_score=score,
            failed_policies=failed,
            passed_policies=passed
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot
