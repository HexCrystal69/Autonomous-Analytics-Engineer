import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.database import engine, Base
from src.routes import (
    auth_router,
    datasets_router,
    quality_router,
    system_router,
    anomalies_router,
    drift_router,
    analytics_router,
    comparisons_router,
    root_cause_router,
    recommendations_router,
    reliability_router,
    sla_router,
    leaderboards_router,
    analytics_dashboard_router,
    observability_router,
    lineage_router,
    freshness_router,
    contracts_router,
    certifications_router,
    monitoring_router,
    impact_router,
    governance_router,
    command_center_router,
    ai_router,
    investigations_router,
    executive_reports_router,
    workflows_router,
    recommendations_lifecycle_router,
    intelligence_dashboard_router,
    tenants_router,
    feature_flags_router,
    retention_router
)



from src.utils.logging import setup_logging
from src.routes.system import REQUEST_COUNT, REQUEST_LATENCY

# Setup logging
setup_logging()

# Initialize database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous Analytics Engineer Platform API",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Metrics Middleware
@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Exclude metrics/health endpoints from metrics collection to avoid noise
    path = request.url.path
    if path not in ["/metrics", "/health"]:
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=path,
            http_status=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=path
        ).observe(duration)
        
    return response

# Register Routers
app.include_router(auth_router)
app.include_router(datasets_router)
app.include_router(quality_router)
app.include_router(system_router)
app.include_router(anomalies_router)
app.include_router(drift_router)
app.include_router(analytics_router)
app.include_router(comparisons_router)
app.include_router(root_cause_router)
app.include_router(recommendations_router)
app.include_router(reliability_router)
app.include_router(sla_router)
app.include_router(leaderboards_router)
app.include_router(analytics_dashboard_router)
app.include_router(observability_router)
app.include_router(lineage_router)
app.include_router(freshness_router)
app.include_router(contracts_router)
app.include_router(certifications_router)
app.include_router(monitoring_router)
app.include_router(impact_router)
app.include_router(governance_router)
app.include_router(command_center_router)
app.include_router(ai_router)
app.include_router(investigations_router)
app.include_router(executive_reports_router)
app.include_router(workflows_router)
app.include_router(recommendations_lifecycle_router)
app.include_router(intelligence_dashboard_router)
app.include_router(tenants_router)
app.include_router(feature_flags_router)
app.include_router(retention_router)




@app.get("/")
def read_root():
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME} API",
        "docs_url": "/docs",
        "status": "running"
    }
