from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "DeFi Thesis & Risk Copilot"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_origin: str = "http://127.0.0.1:3000"
    database_url: str = "sqlite:///./defi_copilot.db"
    llm_synthesis_enabled: bool = False
    llm_provider: str = "ollama"
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
    admin_email: str = "admin@example.local"
    admin_bootstrap_token: str = ""
    admin_password: str = ""
    auth_secret_key: str = ""
    credential_encryption_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
