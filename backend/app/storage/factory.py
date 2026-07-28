from app.core.config import Settings, get_settings
from app.storage.base import PrivateObjectStorage, StorageConfigurationError
from app.storage.supabase import SupabasePrivateObjectStorage


def create_private_object_storage(
    settings: Settings | None = None,
) -> PrivateObjectStorage:
    configured = settings or get_settings()
    if not configured.knowledge_storage_enabled:
        raise StorageConfigurationError("Private knowledge storage is disabled")
    return SupabasePrivateObjectStorage(
        supabase_url=configured.supabase_url,
        service_role_key=configured.supabase_service_role_key,
        bucket=configured.supabase_storage_bucket,
        timeout_seconds=configured.supabase_storage_timeout_seconds,
    )
