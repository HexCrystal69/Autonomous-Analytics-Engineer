import os
from abc import ABC, abstractmethod
from typing import Optional

class SecretProvider(ABC):
    @abstractmethod
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        pass

class EnvSecretProvider(SecretProvider):
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.environ.get(key, default)

class VaultSecretProvider(SecretProvider):
    def __init__(self, token: Optional[str] = None):
        self.token = token

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        # Fallback to local env variables if connection token is missing
        if not self.token:
            return os.environ.get(key, default)
        # Mock vault secret
        return os.environ.get(key, default)

class SecretManager:
    _provider: SecretProvider = EnvSecretProvider()

    @classmethod
    def set_provider(cls, provider: SecretProvider):
        cls._provider = provider

    @classmethod
    def get_secret(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        return cls._provider.get_secret(key, default)
