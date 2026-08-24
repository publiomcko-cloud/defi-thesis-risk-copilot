from functools import lru_cache
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "DeFi Thesis & Risk Copilot"
    public_demo_mode: bool = False
    app_version: str = "0.1.0"
    deployment_commit: str = ""
    observability_enabled: bool = False
    observability_release_id: str = ""
    observability_sampling_rate: float = 1.0
    observability_export_timeout_seconds: float = 2.0
    observability_export_queue_size: int = 100
    observability_clock_timezone: str = "UTC"
    operations_monitoring_enabled: bool = False
    operations_alert_evaluation_enabled: bool = False
    operations_synthetic_checks_enabled: bool = False
    operations_synthetic_allowed_origins: str = ""
    operations_monitoring_window_hours: int = 24
    operations_monitoring_event_limit: int = 1_000
    operations_alert_queue_depth: int = 25
    operations_alert_queue_age_seconds: int = 900
    operations_alert_dead_letter_count: int = 1
    operations_alert_stale_worker_count: int = 1
    operations_alert_retrieval_empty_rate_percent: float = 80.0
    operations_alert_retrieval_latency_ms: int = 5_000
    operations_exercises_enabled: bool = False
    operations_exercises_isolated: bool = False
    operations_exercise_timeout_seconds: int = 180
    controlled_rag_validation_enabled: bool = False
    controlled_rag_validation_isolated: bool = False
    backup_restore_drill_enabled: bool = False
    backup_retention_guard_enabled: bool = False
    backup_restore_evidence_reference: str = ""
    backup_rpo_hours: int = 24
    backup_rto_minutes: int = 240
    public_compute_rate_limit_per_minute: int = 20
    rate_limiting_enabled: bool = False
    rate_limiting_mode: str = "shadow"
    rate_limit_key_pepper: str = ""
    rate_limit_trusted_proxy_cidrs: str = ""
    rate_limit_retention_seconds: int = 86_400
    rate_limit_public_compute_burst_limit: int = 20
    rate_limit_public_compute_burst_window_seconds: int = 60
    rate_limit_public_compute_sustained_limit: int = 120
    rate_limit_public_compute_sustained_window_seconds: int = 3_600
    rate_limit_authenticated_compute_burst_limit: int = 60
    rate_limit_authenticated_compute_burst_window_seconds: int = 60
    rate_limit_authenticated_compute_sustained_limit: int = 1_000
    rate_limit_authenticated_compute_sustained_window_seconds: int = 3_600
    rate_limit_job_submit_burst_limit: int = 10
    rate_limit_job_submit_burst_window_seconds: int = 60
    rate_limit_job_submit_sustained_limit: int = 100
    rate_limit_job_submit_sustained_window_seconds: int = 3_600
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_origin: str = "http://127.0.0.1:3000"
    api_max_request_bytes: int = 1 * 1024 * 1024
    security_csp_mode: str = "report_only"
    security_csp_report_uri: str = ""
    security_hsts_enabled: bool = False
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
    ownership_transfer_recent_auth_seconds: int = 600
    ownership_transfer_legacy_local_recent_auth_enabled: bool = False
    knowledge_storage_enabled: bool = False
    supabase_storage_bucket: str = "private-knowledge"
    supabase_storage_timeout_seconds: float = 20.0
    knowledge_upload_max_bytes: int = 10 * 1024 * 1024
    knowledge_upload_chunk_bytes: int = 64 * 1024
    knowledge_upload_scanning_required: bool = False
    knowledge_upload_scanner_url: str = ""
    knowledge_upload_scanner_timeout_seconds: float = 10.0
    document_ingest_enabled: bool = False
    knowledge_ingest_max_bytes: int = 10 * 1024 * 1024
    knowledge_ingest_max_text_bytes: int = 2 * 1024 * 1024
    knowledge_ingest_max_pdf_pages: int = 100
    knowledge_chunk_max_characters: int = 2_000
    knowledge_embeddings_enabled: bool = False
    knowledge_embedding_profile_id: str = "kembprof_local_hash_384_v1"
    knowledge_embedding_provider: str = "local_deterministic"
    knowledge_embedding_model: str = "local-hash-384-v1"
    knowledge_embedding_dimensions: int = 384
    knowledge_shadow_retrieval_enabled: bool = False
    knowledge_shadow_retrieval_top_k: int = 4
    knowledge_public_corpus_import_enabled: bool = False
    knowledge_pgvector_primary_enabled: bool = False
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
    product_analytics_enabled: bool = False
    product_analytics_policy_version: str = "phase20b-2026-07-31"
    product_analytics_retention_days: int = 30
    product_analytics_withdrawal_deletion_hours: int = 24
    product_analytics_decision_retention_days: int = 30
    schedule_dispatch_enabled: bool = False
    schedule_dispatch_batch_size: int = 25
    schedule_history_retention_days: int = 30
    schedule_dispatch_poll_seconds: float = 5.0
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
        allowed_origins = [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]
        if not allowed_origins or any(not _is_origin(origin) for origin in allowed_origins):
            raise ValueError("FRONTEND_ORIGIN must contain one or more absolute origins without paths")
        if self.api_max_request_bytes < 1:
            raise ValueError("API_MAX_REQUEST_BYTES must be positive")
        if self.security_csp_mode not in {"disabled", "report_only", "enforce"}:
            raise ValueError("SECURITY_CSP_MODE must be disabled, report_only, or enforce")
        if self.security_csp_report_uri and not self.security_csp_report_uri.startswith("/"):
            raise ValueError("SECURITY_CSP_REPORT_URI must be a relative path")
        if not 0 <= self.observability_sampling_rate <= 1:
            raise ValueError("OBSERVABILITY_SAMPLING_RATE must be between 0 and 1")
        if not 0 < self.observability_export_timeout_seconds <= 30:
            raise ValueError("OBSERVABILITY_EXPORT_TIMEOUT_SECONDS must be between 0 and 30")
        if not 1 <= self.observability_export_queue_size <= 10_000:
            raise ValueError("OBSERVABILITY_EXPORT_QUEUE_SIZE must be between 1 and 10000")
        if self.observability_clock_timezone != "UTC":
            raise ValueError("OBSERVABILITY_CLOCK_TIMEZONE must be UTC")
        if self.operations_alert_evaluation_enabled and not self.operations_monitoring_enabled:
            raise ValueError("OPERATIONS_ALERT_EVALUATION_ENABLED requires OPERATIONS_MONITORING_ENABLED")
        if self.operations_synthetic_checks_enabled and not self.operations_monitoring_enabled:
            raise ValueError("OPERATIONS_SYNTHETIC_CHECKS_ENABLED requires OPERATIONS_MONITORING_ENABLED")
        if self.operations_exercises_enabled and self.app_env == "production":
            raise ValueError("OPERATIONS_EXERCISES_ENABLED cannot run in production")
        if self.operations_exercises_enabled and not self.operations_exercises_isolated:
            raise ValueError("OPERATIONS_EXERCISES_ENABLED requires OPERATIONS_EXERCISES_ISOLATED=true")
        if not 5 <= self.operations_exercise_timeout_seconds <= 600:
            raise ValueError("OPERATIONS_EXERCISE_TIMEOUT_SECONDS must be between 5 and 600")
        if self.controlled_rag_validation_isolated and not self.controlled_rag_validation_enabled:
            raise ValueError(
                "CONTROLLED_RAG_VALIDATION_ISOLATED requires CONTROLLED_RAG_VALIDATION_ENABLED"
            )
        if min(
            self.operations_monitoring_window_hours,
            self.operations_monitoring_event_limit,
            self.operations_alert_queue_depth,
            self.operations_alert_queue_age_seconds,
            self.operations_alert_dead_letter_count,
            self.operations_alert_stale_worker_count,
            self.operations_alert_retrieval_latency_ms,
        ) < 1:
            raise ValueError("Phase 19 operations monitoring thresholds must be positive")
        if not 0 <= self.operations_alert_retrieval_empty_rate_percent <= 100:
            raise ValueError("OPERATIONS_ALERT_RETRIEVAL_EMPTY_RATE_PERCENT must be between 0 and 100")
        if min(self.backup_rpo_hours, self.backup_rto_minutes) < 1:
            raise ValueError("BACKUP_RPO_HOURS and BACKUP_RTO_MINUTES must be positive")
        if self.backup_retention_guard_enabled and not self.backup_restore_evidence_reference.strip():
            raise ValueError("BACKUP_RESTORE_EVIDENCE_REFERENCE is required when BACKUP_RETENTION_GUARD_ENABLED")
        if len(self.backup_restore_evidence_reference) > 255:
            raise ValueError("BACKUP_RESTORE_EVIDENCE_REFERENCE must not exceed 255 characters")
        if len(self.observability_release_id) > 128:
            raise ValueError("OBSERVABILITY_RELEASE_ID must not exceed 128 characters")
        if self.rate_limiting_mode not in {"shadow", "enforce"}:
            raise ValueError("RATE_LIMITING_MODE must be shadow or enforce")
        if self.rate_limiting_enabled and self.app_env == "production" and not self.rate_limit_key_pepper:
            raise ValueError("RATE_LIMIT_KEY_PEPPER is required when production rate limiting is enabled")
        rate_limit_values = (
            self.public_compute_rate_limit_per_minute,
            self.rate_limit_retention_seconds,
            self.rate_limit_public_compute_burst_limit,
            self.rate_limit_public_compute_burst_window_seconds,
            self.rate_limit_public_compute_sustained_limit,
            self.rate_limit_public_compute_sustained_window_seconds,
            self.rate_limit_authenticated_compute_burst_limit,
            self.rate_limit_authenticated_compute_burst_window_seconds,
            self.rate_limit_authenticated_compute_sustained_limit,
            self.rate_limit_authenticated_compute_sustained_window_seconds,
            self.rate_limit_job_submit_burst_limit,
            self.rate_limit_job_submit_burst_window_seconds,
            self.rate_limit_job_submit_sustained_limit,
            self.rate_limit_job_submit_sustained_window_seconds,
        )
        if min(rate_limit_values) < 1:
            raise ValueError("Rate-limit windows, limits, and retention must be positive")
        provider = self.auth_provider.lower()
        if provider not in {"legacy_local", "supabase"}:
            raise ValueError("AUTH_PROVIDER must be legacy_local or supabase")
        if self.auth_enabled and provider == "legacy_local" and self.app_env == "production":
            raise ValueError("legacy_local authentication is not allowed in production")
        if not 1 <= self.ownership_transfer_recent_auth_seconds <= 600:
            raise ValueError("OWNERSHIP_TRANSFER_RECENT_AUTH_SECONDS must be between 1 and 600")
        if self.ownership_transfer_legacy_local_recent_auth_enabled and self.app_env == "production":
            raise ValueError("Legacy local recent-auth support is not allowed in production")
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
        if not self.product_analytics_policy_version.strip() or len(self.product_analytics_policy_version) > 32:
            raise ValueError("PRODUCT_ANALYTICS_POLICY_VERSION must be between 1 and 32 characters")
        if self.product_analytics_retention_days != 30:
            raise ValueError("PRODUCT_ANALYTICS_RETENTION_DAYS must remain 30 for Phase 20B")
        if self.product_analytics_decision_retention_days != 30:
            raise ValueError("PRODUCT_ANALYTICS_DECISION_RETENTION_DAYS must remain 30 for Phase 20B")
        if not 1 <= self.product_analytics_withdrawal_deletion_hours <= 24:
            raise ValueError("PRODUCT_ANALYTICS_WITHDRAWAL_DELETION_HOURS must be between 1 and 24")
        if self.app_env == "production" and self.product_analytics_enabled:
            raise ValueError(
                "PRODUCT_ANALYTICS_ENABLED cannot run in production before qualified privacy/legal approval"
            )
        if self.schedule_dispatch_enabled and (not self.jobs_enabled or not self.worker_api_enabled):
            raise ValueError("SCHEDULE_DISPATCH_ENABLED requires JOBS_ENABLED and WORKER_API_ENABLED")
        if self.schedule_dispatch_enabled and self.app_env == "production":
            raise ValueError("SCHEDULE_DISPATCH_ENABLED cannot run in production before Phase 20C approval")
        if not 1 <= self.schedule_dispatch_batch_size <= 100:
            raise ValueError("SCHEDULE_DISPATCH_BATCH_SIZE must be between 1 and 100")
        if self.schedule_history_retention_days != 30:
            raise ValueError("SCHEDULE_HISTORY_RETENTION_DAYS must remain 30 for Phase 20C")
        if not 0.1 <= self.schedule_dispatch_poll_seconds <= 60:
            raise ValueError("SCHEDULE_DISPATCH_POLL_SECONDS must be between 0.1 and 60")
        if self.knowledge_storage_enabled:
            if self.app_env == "production" and (
                not self.supabase_url or not self.supabase_service_role_key
            ):
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required when "
                    "production knowledge storage is enabled"
                )
            if (
                not self.supabase_storage_bucket
                or "/" in self.supabase_storage_bucket
                or len(self.supabase_storage_bucket) > 128
                or any(
                    character not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
                    for character in self.supabase_storage_bucket
                )
                or self.supabase_storage_timeout_seconds <= 0
            ):
                raise ValueError("Private knowledge storage configuration is invalid")
        if (
            self.knowledge_upload_max_bytes < 1
            or self.knowledge_upload_chunk_bytes < 1024
            or self.knowledge_upload_chunk_bytes > self.knowledge_upload_max_bytes
        ):
            raise ValueError("Knowledge upload limits are invalid")
        if self.knowledge_upload_scanner_timeout_seconds <= 0:
            raise ValueError("KNOWLEDGE_UPLOAD_SCANNER_TIMEOUT_SECONDS must be positive")
        if self.knowledge_upload_scanning_required:
            if not self.knowledge_storage_enabled:
                raise ValueError("KNOWLEDGE_UPLOAD_SCANNING_REQUIRED requires KNOWLEDGE_STORAGE_ENABLED")
            if not _is_scanner_url(self.knowledge_upload_scanner_url):
                raise ValueError("KNOWLEDGE_UPLOAD_SCANNER_URL must be an absolute HTTP(S) URL without credentials")
        if self.app_env == "production" and self.knowledge_storage_enabled and not self.knowledge_upload_scanning_required:
            raise ValueError("Production knowledge storage requires KNOWLEDGE_UPLOAD_SCANNING_REQUIRED")
        if (
            self.knowledge_ingest_max_bytes < 1
            or self.knowledge_ingest_max_bytes > self.knowledge_upload_max_bytes
            or self.knowledge_ingest_max_text_bytes < 1
            or self.knowledge_ingest_max_pdf_pages < 1
            or self.knowledge_chunk_max_characters < 256
        ):
            raise ValueError("Knowledge ingestion limits are invalid")
        if self.document_ingest_enabled and (
            not self.jobs_enabled or not self.worker_api_enabled or not self.knowledge_storage_enabled
        ):
            raise ValueError(
                "DOCUMENT_INGEST_ENABLED requires JOBS_ENABLED, WORKER_API_ENABLED, and KNOWLEDGE_STORAGE_ENABLED"
            )
        if self.knowledge_embeddings_enabled and (
            not self.jobs_enabled or not self.worker_api_enabled
        ):
            raise ValueError(
                "KNOWLEDGE_EMBEDDINGS_ENABLED requires JOBS_ENABLED and WORKER_API_ENABLED"
            )
        if self.knowledge_shadow_retrieval_enabled and not self.knowledge_embeddings_enabled:
            raise ValueError(
                "KNOWLEDGE_SHADOW_RETRIEVAL_ENABLED requires KNOWLEDGE_EMBEDDINGS_ENABLED"
            )
        if self.knowledge_pgvector_primary_enabled and not self.knowledge_shadow_retrieval_enabled:
            raise ValueError(
                "KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED requires KNOWLEDGE_SHADOW_RETRIEVAL_ENABLED"
            )
        if self.app_env == "production" and self.knowledge_pgvector_primary_enabled:
            raise ValueError(
                "KNOWLEDGE_PGVECTOR_PRIMARY_ENABLED cannot run in production before Phase 22 approval"
            )
        if not 1 <= self.knowledge_shadow_retrieval_top_k <= 20:
            raise ValueError("KNOWLEDGE_SHADOW_RETRIEVAL_TOP_K must be between 1 and 20")
        if (
            not self.knowledge_embedding_profile_id.startswith("kembprof_")
            or self.knowledge_embedding_provider != "local_deterministic"
            or self.knowledge_embedding_model != "local-hash-384-v1"
            or self.knowledge_embedding_dimensions != 384
        ):
            raise ValueError(
                "Only the approved local deterministic 384-dimension embedding profile is supported"
            )
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


def _is_origin(value: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
        and not parsed.username
        and not parsed.password
        and parsed.path in {"", "/"}
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    )


def _is_scanner_url(value: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.netloc)
        and not parsed.username
        and not parsed.password
        and not parsed.fragment
    )
