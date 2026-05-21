from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "cloudnative-devopslab"
    app_env: str = "dev"
    app_version: str = "0.1.0"
    git_sha: str = "local"
    image_digest: str = "unknown"
    fault_mode: bool = False
    readiness_enabled: bool = True
    slow_request_ms: int = 0
    slo_availability_target: float = 99.9
    slo_latency_p95_ms: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
