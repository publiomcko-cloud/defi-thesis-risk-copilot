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
    current_terms_version: str = "2026-07-20"
    current_privacy_version: str = "2026-07-20"
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
    bff_audit_secret: str = ""
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
    vast_real_rentals_enabled: bool = False
    vast_reconciliation_profile: str = "unverified"
    jobs_enabled: bool = False
    worker_api_enabled: bool = False
    async_analysis_enabled: bool = False
    vast_job_enabled: bool = False
    job_default_max_attempts: int = 3
    job_lease_seconds: int = 60
    job_heartbeat_seconds: int = 20
    job_max_lease_extension_seconds: int = 720
    analysis_job_max_attempt_runtime_seconds: int = 300
    job_cleanup_grace_seconds: int = 60
    vast_reconciliation_grace_seconds: int = 30
    job_max_queue_age_seconds: int = 3600
    job_event_retention_days: int = 90
    job_terminal_retention_days: int = 30
    job_max_input_bytes: int = 65_536
    job_max_result_bytes: int = 262_144
    job_max_progress_message_length: int = 512
    job_global_pending_limit: int = 100
    job_global_running_limit: int = 4
    job_user_pending_limit: int = 10
    job_user_running_limit: int = 2
    job_org_pending_limit: int = 50
    job_org_running_limit: int = 8
    job_provider_pending_limit: int = 25
    job_provider_running_limit: int = 4
    job_daily_cost_budget_microusd: int = 0
    job_claim_scan_limit: int = 25
    job_retry_base_seconds: int = 5
    job_retry_max_seconds: int = 300
    worker_stale_seconds: int = 120
    worker_poll_seconds: float = 2.0
    worker_protocol_version: str = "v1"
    worker_token_pepper: str = ""

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
        if self.auth_enabled and self.app_env == "production" and not self.bff_audit_secret:
            raise ValueError("BFF_AUDIT_SECRET is required when production authentication is enabled")
        if self.worker_api_enabled and not self.jobs_enabled:
            raise ValueError("WORKER_API_ENABLED requires JOBS_ENABLED")
        if self.async_analysis_enabled and not self.jobs_enabled:
            raise ValueError("ASYNC_ANALYSIS_ENABLED requires JOBS_ENABLED")
        if self.vast_job_enabled and not self.jobs_enabled:
            raise ValueError("VAST_JOB_ENABLED requires JOBS_ENABLED")
        if self.worker_api_enabled and self.app_env == "production" and not self.worker_token_pepper:
            raise ValueError("WORKER_TOKEN_PEPPER is required when production worker API is enabled")
        if self.job_default_max_attempts < 1:
            raise ValueError("JOB_DEFAULT_MAX_ATTEMPTS must be positive")
        if self.job_heartbeat_seconds < 1 or self.job_lease_seconds < self.job_heartbeat_seconds:
            raise ValueError("JOB_LEASE_SECONDS must be at least JOB_HEARTBEAT_SECONDS")
        if self.job_max_lease_extension_seconds < self.job_lease_seconds:
            raise ValueError("JOB_MAX_LEASE_EXTENSION_SECONDS must cover one lease")
        if self.analysis_job_max_attempt_runtime_seconds < self.job_lease_seconds:
            raise ValueError("ANALYSIS_JOB_MAX_ATTEMPT_RUNTIME_SECONDS must cover one lease")
        vast_horizon = self.vast_startup_timeout_seconds + self.vast_reconciliation_grace_seconds + self.job_cleanup_grace_seconds
        if self.job_max_lease_extension_seconds < max(self.analysis_job_max_attempt_runtime_seconds, vast_horizon):
            raise ValueError("JOB_MAX_LEASE_EXTENSION_SECONDS must cover every registered job horizon")
        if min(
            self.job_max_queue_age_seconds,
            self.job_event_retention_days,
            self.job_terminal_retention_days,
            self.job_max_input_bytes,
            self.job_max_result_bytes,
            self.job_max_progress_message_length,
            self.job_global_pending_limit,
            self.job_global_running_limit,
            self.job_user_pending_limit,
            self.job_user_running_limit,
            self.job_org_pending_limit,
            self.job_org_running_limit,
            self.job_provider_pending_limit,
            self.job_provider_running_limit,
            self.job_daily_cost_budget_microusd,
            self.job_claim_scan_limit,
            self.job_retry_base_seconds,
            self.job_retry_max_seconds,
            self.worker_stale_seconds,
        ) < 0:
            raise ValueError("Phase 17 job limits cannot be negative")
        if self.job_claim_scan_limit < 1 or self.job_retry_base_seconds < 1 or self.job_retry_max_seconds < self.job_retry_base_seconds:
            raise ValueError("Phase 17 worker retry and claim settings are invalid")
        if self.worker_stale_seconds < self.job_heartbeat_seconds or self.worker_poll_seconds <= 0:
            raise ValueError("Phase 17 worker freshness settings are invalid")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
