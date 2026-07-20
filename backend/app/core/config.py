from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "DeFi Thesis & Risk Copilot"
    public_demo_mode: bool = False
    app_version: str = "0.1.0"
    deployment_commit: str = ""
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_origin: str = "http://127.0.0.1:3000"
    database_url: str = "sqlite:///./defi_copilot.db"
    llm_synthesis_enabled: bool = False
    llm_provider: str = "disabled"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    openai_compatible_base_url: str = ""
    openai_compatible_api_key: str = ""
    openai_compatible_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 8.0
    defillama_base_url: str = "https://api.llama.fi"
    rag_semantic_enabled: bool = False
    rag_embedding_provider: str = "local_semantic"
    rag_hybrid_keyword_weight: float = 0.45
    rag_hybrid_vector_weight: float = 0.45
    rag_hybrid_metadata_weight: float = 0.10
    auth_enabled: bool = False
    auth_provider: str = "legacy_local"
    require_verified_email: bool = True
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_jwks_url: str = ""
    supabase_jwt_issuer: str = ""
    supabase_jwt_audience: str = "authenticated"
    supabase_service_role_key: str = ""
    session_cookie_name: str = "defi_copilot_session"
    anonymous_session_cookie_name: str = "defi_copilot_anon"
    cookie_secure: bool = True
    cookie_samesite: str = "lax"
    cookie_domain: str = ""
    admin_mfa_required: bool = False
    anonymous_retention_hours: int = 24
    deleted_account_retention_days: int = 30
    default_user_plan: str = "free"
    quota_anonymous_analyses_per_day: int = 5
    quota_free_analyses_per_day: int = 25
    quota_free_simulations_per_day: int = 100
    quota_free_options_per_day: int = 100
    quota_free_market_data_per_day: int = 100
    quota_free_saved_theses: int = 50
    quota_free_watchlists: int = 25
    quota_admin_exempt: bool = True
    admin_email: str = "admin@example.local"
    admin_bootstrap_token: str = ""
    admin_password: str = ""
    auth_secret_key: str = ""
    credential_encryption_key: str = ""
    vast_enabled: bool = False
    vast_api_base_url: str = "https://console.vast.ai/api/v0"
    vast_api_key: str = ""
    vast_credential_name: str = "vast_ai_default"
    vast_max_hourly_cost_usd: float = 0.50
    vast_max_session_minutes: int = 30
    vast_max_active_instances: int = 1
    vast_gpu_allowlist: str = "RTX_4090,RTX_3090,A5000,A6000"
    vast_min_gpu_ram_gb: int = 16
    vast_disk_gb: int = 40
    vast_require_verified: bool = True
    vast_auto_destroy: bool = True
    vast_idle_timeout_seconds: int = 300
    vast_image: str = ""
    vast_model: str = ""
    vast_container_port: int = 8000
    vast_startup_timeout_seconds: int = 600
    vast_poll_interval_seconds: int = 10
    vast_dry_run: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> "Settings":
        provider = self.auth_provider.lower()
        if provider not in {"legacy_local", "supabase"}:
            raise ValueError("AUTH_PROVIDER must be legacy_local or supabase")
        if self.auth_enabled and provider == "legacy_local" and self.app_env == "production":
            raise ValueError("legacy_local authentication is not allowed in production")
        if self.auth_enabled and provider == "supabase":
            missing = [
                name
                for name, value in {
                    "SUPABASE_URL": self.supabase_url,
                    "SUPABASE_JWKS_URL": self.supabase_jwks_url,
                    "SUPABASE_JWT_ISSUER": self.supabase_jwt_issuer,
                }.items()
                if not value
            ]
            if missing and self.app_env == "production":
                raise ValueError(
                    "Supabase authentication is enabled but required variables are missing: "
                    + ", ".join(missing)
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
