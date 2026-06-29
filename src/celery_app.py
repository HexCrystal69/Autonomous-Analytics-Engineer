from celery import Celery
from src.config import settings

celery_app = Celery(
    "analytics_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "src.tasks.profile_tasks",
        "src.tasks.quality_tasks",
        "src.tasks.analytics_tasks",
        "src.tasks.monitoring_tasks",
        "src.tasks.governance_tasks",
        "src.tasks.impact_tasks",
        "src.tasks.intelligence_tasks",
        "src.tasks.workflow_tasks"
    ]
)



celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
