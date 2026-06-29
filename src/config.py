import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Autonomous Analytics Engineer"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "supersecretkeychangeinproduction"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # DB / Cache / Broker
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/analytics_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Storage
    STORAGE_PROVIDER: str = "local"
    STORAGE_DIR: str = "storage_data"
    MAX_FILE_SIZE_MB: int = 50

    # Drift Severity Thresholds
    PSI_LOW_LIMIT: float = 0.10
    PSI_MED_LIMIT: float = 0.25

    MEAN_SHIFT_LOW_LIMIT: float = 0.10
    MEAN_SHIFT_MED_LIMIT: float = 0.25

    CARD_DRIFT_LOW_LIMIT: float = 0.10
    CARD_DRIFT_MED_LIMIT: float = 0.30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Ensure local storage directory exists
if settings.STORAGE_PROVIDER == "local":
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
