import pytest
from src.services.secret_provider import SecretManager, EnvSecretProvider, VaultSecretProvider
from src.services.retention_engine import RetentionEngine

def test_chaos_secrets_vault_fallback(db):
    # Simulated Vault connection outage: no token configured
    vault_provider = VaultSecretProvider(token=None)
    SecretManager.set_provider(vault_provider)

    # Assumes fallback to local env
    assert SecretManager.get_secret("DB_HOST", "localhost") == "localhost"

def test_chaos_retention_purge_empty_db(db):
    import uuid
    # Retention engine should handle non-existent datasets gracefully without crashing
    exec_record = RetentionEngine.execute_purges(db, uuid.uuid4())
    assert exec_record.status == "SUCCESS"
    assert exec_record.purged_records_count == 0
