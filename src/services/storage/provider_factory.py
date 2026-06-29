from src.config import settings
from src.services.storage.base import BaseStorageProvider
from src.services.storage.local_storage import LocalStorageProvider

class StorageProviderFactory:
    @staticmethod
    def get_provider() -> BaseStorageProvider:
        if settings.STORAGE_PROVIDER == "local":
            return LocalStorageProvider()
        else:
            raise ValueError(f"Unknown storage provider: {settings.STORAGE_PROVIDER}")
