from src.routes.auth import router as auth_router
from src.routes.datasets import router as datasets_router
from src.routes.quality import router as quality_router
from src.routes.system import router as system_router
from src.routes.anomalies import router as anomalies_router
from src.routes.drift import router as drift_router
from src.routes.analytics import router as analytics_router
from src.routes.comparisons import router as comparisons_router
from src.routes.root_cause import router as root_cause_router
from src.routes.recommendations import router as recommendations_router
from src.routes.reliability import router as reliability_router
from src.routes.sla import router as sla_router
from src.routes.leaderboards import router as leaderboards_router
from src.routes.analytics_dashboard import router as analytics_dashboard_router
from src.routes.observability import router as observability_router
from src.routes.lineage import router as lineage_router
from src.routes.freshness import router as freshness_router
from src.routes.contracts import router as contracts_router
from src.routes.certifications import router as certifications_router
from src.routes.monitoring import router as monitoring_router
from src.routes.impact import router as impact_router
from src.routes.governance import router as governance_router
from src.routes.command_center import router as command_center_router
from src.routes.ai import router as ai_router
from src.routes.investigations import router as investigations_router
from src.routes.executive_reports import router as executive_reports_router
from src.routes.workflows import router as workflows_router
from src.routes.recommendations import router as recommendations_lifecycle_router
from src.routes.intelligence_dashboard import router as intelligence_dashboard_router
from src.routes.tenants import router as tenants_router
from src.routes.feature_flags import router as feature_flags_router
from src.routes.retention import router as retention_router

__all__ = [
    "auth_router",
    "datasets_router",
    "quality_router",
    "system_router",
    "anomalies_router",
    "drift_router",
    "analytics_router",
    "comparisons_router",
    "root_cause_router",
    "recommendations_router",
    "reliability_router",
    "sla_router",
    "leaderboards_router",
    "analytics_dashboard_router",
    "observability_router",
    "lineage_router",
    "freshness_router",
    "contracts_router",
    "certifications_router",
    "monitoring_router",
    "impact_router",
    "governance_router",
    "command_center_router",
    "ai_router",
    "investigations_router",
    "executive_reports_router",
    "workflows_router",
    "recommendations_lifecycle_router",
    "intelligence_dashboard_router",
    "tenants_router",
    "feature_flags_router",
    "retention_router"
]



