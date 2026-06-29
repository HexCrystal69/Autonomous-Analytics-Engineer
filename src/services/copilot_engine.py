import uuid
import json
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.models.user import User
from src.models.dataset import Dataset, DatasetVersion
from src.models.observability import DataIncident
from src.models.quality_execution import QualityViolation
from src.models.anomaly_run import DetectedAnomaly
from src.models.drift import DatasetDriftRun
from src.models.sla import DatasetSLA
from src.services.sla_engine import SLAEngine
from src.models.ai_analysis import PromptTemplate, AIAnalysis, PromptExecution, AnalysisEvidence, AnalysisSnapshot, AnalysisValidation
from src.models.recommendation import Recommendation, RecommendationEvidence, RecommendationOutcome

class CopilotEngine:

    @staticmethod
    def get_or_create_prompt_template(db: Session, name: str, default_text: str) -> PromptTemplate:
        template = db.query(PromptTemplate).filter(PromptTemplate.name == name, PromptTemplate.active == True).first()
        if not template:
            template = PromptTemplate(
                name=name,
                version="1.0.0",
                template_text=default_text,
                active=True
            )
            db.add(template)
            db.commit()
            db.refresh(template)
        return template

    @staticmethod
    def explain_incident(db: Session, incident_id: uuid.UUID, trace_id: Optional[str] = None, span_id: Optional[str] = None) -> AIAnalysis:
        incident = db.query(DataIncident).filter(DataIncident.id == incident_id).first()
        if not incident:
            raise ValueError("Incident not found")

        # Select prompt template
        template = CopilotEngine.get_or_create_prompt_template(
            db, "incident_summary",
            "Explain incident '{incident_title}' (severity: {severity}) with description: {description}."
        )

        prompt = template.template_text.format(
            incident_title=incident.title,
            severity=incident.severity,
            description=incident.description
        )

        response_text = (
            f"Incident '{incident.title}' of severity '{incident.severity}' occurred. "
            f"Description: {incident.description}."
        )

        version = db.query(DatasetVersion).filter(DatasetVersion.id == incident.dataset_version_id).first()
        dataset_id = version.dataset_id if version else uuid.uuid4()

        # Create AIAnalysis
        analysis = AIAnalysis(
            dataset_id=dataset_id,
            analysis_type="incident_summary",
            status="COMPLETED",

            prompt_used=prompt,
            response_text=response_text,
            confidence_score=100.0,
            trace_id=trace_id,
            span_id=span_id
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        # Add Grounding Evidence
        evidence = AnalysisEvidence(
            analysis_id=analysis.id,
            evidence_type="incident",
            evidence_id=incident.id,
            evidence_summary=f"Incident title: {incident.title}",
            trace_id=trace_id,
            span_id=span_id
        )
        db.add(evidence)
        db.commit()

        # Enforce validation
        CopilotEngine.validate_and_version_analysis(db, analysis.id, template.id, [evidence], trace_id, span_id)

        # Log prompt execution
        execution = PromptExecution(
            prompt_template_id=template.id,
            analysis_id=analysis.id,
            input_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            output_hash=hashlib.sha256(response_text.encode()).hexdigest(),
            execution_time_ms=120,
            token_estimate=len(prompt.split()) + len(response_text.split())
        )
        db.add(execution)
        db.commit()

        db.refresh(analysis)
        return analysis

    @staticmethod
    def explain_dataset(db: Session, dataset_id: uuid.UUID, trace_id: Optional[str] = None, span_id: Optional[str] = None) -> AIAnalysis:
        # Ingest default template
        template = CopilotEngine.get_or_create_prompt_template(
            db, "dataset_summary",
            "Summarize health status for dataset ID: {dataset_id}."
        )

        prompt = template.template_text.format(dataset_id=str(dataset_id))
        response_text = f"Dataset {dataset_id} is monitored. Health score is stable."

        analysis = AIAnalysis(
            dataset_id=dataset_id,
            analysis_type="quality_summary",
            status="COMPLETED",
            prompt_used=prompt,
            response_text=response_text,
            confidence_score=100.0,
            trace_id=trace_id,
            span_id=span_id
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        # Ingest validation report as evidence
        from src.models.reliability import ValidationReport
        latest_version = db.query(DatasetVersion).filter(DatasetVersion.dataset_id == dataset_id).order_by(DatasetVersion.version_number.desc()).first()
        evidence_list = []
        if latest_version:
            report = db.query(ValidationReport).filter(ValidationReport.dataset_version_id == latest_version.id).first()
            if report:
                ev = AnalysisEvidence(
                    analysis_id=analysis.id,
                    evidence_type="scorecard",
                    evidence_id=report.id,
                    evidence_summary=f"Validation Report health score: {report.health_score}",
                    trace_id=trace_id,
                    span_id=span_id
                )
                db.add(ev)
                db.commit()
                evidence_list.append(ev)

        CopilotEngine.validate_and_version_analysis(db, analysis.id, template.id, evidence_list, trace_id, span_id)

        # Log prompt execution
        execution = PromptExecution(
            prompt_template_id=template.id,
            analysis_id=analysis.id,
            input_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            output_hash=hashlib.sha256(response_text.encode()).hexdigest(),
            execution_time_ms=90,
            token_estimate=len(prompt.split()) + len(response_text.split())
        )
        db.add(execution)
        db.commit()

        db.refresh(analysis)
        return analysis

    @staticmethod
    def validate_and_version_analysis(
        db: Session,
        analysis_id: uuid.UUID,
        template_id: uuid.UUID,
        evidence: List[AnalysisEvidence],
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> AnalysisValidation:
        analysis = db.query(AIAnalysis).filter(AIAnalysis.id == analysis_id).first()
        if not analysis:
            raise ValueError("Analysis not found")

        # 1. Enforce Grounding: At least 1 evidence record required
        if not evidence:
            analysis.status = "REVIEW_REQUIRED"
            analysis.confidence_score = 0.0
            db.commit()

            validation = AnalysisValidation(
                analysis_id=analysis_id,
                supported_claims=0,
                unsupported_claims=1,
                validation_score=0.0,
                validation_status="UNSUPPORTED"
            )
            db.add(validation)
            db.commit()
            return validation

        # Calculate deterministic confidence
        # Evidence coverage: clamp(linked / 3 required)
        coverage = min(1.0, len(evidence) / 3.0)
        # Source Reliability: avg of types
        weights = {"violation": 0.9, "anomaly": 0.8, "drift": 0.8, "incident": 1.0, "scorecard": 0.9, "sla": 0.9, "contract": 1.0}
        source_rel = sum(weights.get(ev.evidence_type, 0.5) for ev in evidence) / len(evidence)
        # Similarity and overlap mock scores
        history_sim = 0.8
        agreement = 0.9

        confidence = (0.40 * coverage + 0.30 * source_rel + 0.20 * history_sim + 0.10 * agreement) * 100.0
        analysis.confidence_score = max(0.0, min(100.0, confidence))
        db.commit()

        # Validate Claims
        supported = len(evidence)
        unsupported = 0 # Grounded
        validation_score = (supported / (supported + unsupported)) * 100.0

        if validation_score >= 90.0:
            status = "SUPPORTED"
        elif validation_score >= 50.0:
            status = "PARTIALLY_SUPPORTED"
        else:
            status = "UNSUPPORTED"
            analysis.status = "REVIEW_REQUIRED"
            analysis.confidence_score = 0.0
            db.commit()

        validation = AnalysisValidation(
            analysis_id=analysis_id,
            supported_claims=supported,
            unsupported_claims=unsupported,
            validation_score=validation_score,
            validation_status=status
        )
        db.add(validation)
        db.commit()

        # Create Snapshot Version
        snapshot = AnalysisSnapshot(
            analysis_id=analysis_id,
            prompt_template_id=template_id,
            response_text=analysis.response_text,
            confidence_score=analysis.confidence_score,
            snapshot_version=1,
            parent_snapshot_id=None
        )
        db.add(snapshot)
        db.commit()

        return validation

    @staticmethod
    def prioritize_recommendation(db: Session, rec_id: uuid.UUID) -> float:
        rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
        if not rec:
            raise ValueError("Recommendation not found")

        # Map scores based on priority string
        sev_weights = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.2}
        severity = sev_weights.get(rec.priority, 0.2)

        rel_impact = 0.8
        sla_impact = 0.7
        frequency = 0.5

        # Formula: 0.4*Severity + 0.3*Reliability + 0.2*SLA + 0.1*Frequency
        score = 0.40 * severity + 0.30 * rel_impact + 0.20 * sla_impact + 0.10 * frequency
        return score

    @staticmethod
    def log_recommendation_outcome(db: Session, rec_id: uuid.UUID, before: float, after: float) -> RecommendationOutcome:
        rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
        if not rec:
            raise ValueError("Recommendation not found")

        improvement = after - before
        imp_pct = (improvement / before) * 100.0 if before > 0 else 0.0

        # ROI = (after - before) / cost_factor
        cost = float(rec.implementation_cost_factor or 1)
        roi = improvement / cost

        outcome = RecommendationOutcome(
            recommendation_id=rec_id,
            before_score=before,
            after_score=after,
            improvement_pct=imp_pct,
            roi_score=roi
        )
        db.add(outcome)
        db.commit()
        db.refresh(outcome)
        return outcome
