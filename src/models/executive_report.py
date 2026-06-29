import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, Float, Integer, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database import Base

class ExecutiveReport(Base):
    __tablename__ = "executive_reports"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    report_name = Column(String, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    report_json = Column(JSON, nullable=False)
    report_quality_score = Column(Float, default=100.0, nullable=False)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sections = relationship("ReportSection", back_populates="report", cascade="all, delete-orphan")
    snapshots = relationship("ExecutiveReportSnapshot", back_populates="report", cascade="all, delete-orphan")

class ReportSection(Base):
    __tablename__ = "report_sections"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    report_id = Column(Uuid, ForeignKey("executive_reports.id", ondelete="CASCADE"), nullable=False)
    section_name = Column(String, nullable=False) # kpi_summary, incident_overview, sla_status, dataset_rankings, trend_forecasts
    content_json = Column(JSON, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    report = relationship("ExecutiveReport", back_populates="sections")

class ExecutiveReportSnapshot(Base):
    __tablename__ = "executive_report_snapshots"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    report_id = Column(Uuid, ForeignKey("executive_reports.id", ondelete="CASCADE"), nullable=False)
    snapshot_version = Column(Integer, default=1, nullable=False)
    report_json = Column(JSON, nullable=False)
    trace_id = Column(String, nullable=True)
    span_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    report = relationship("ExecutiveReport", back_populates="snapshots")
