from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "200iq-moments"
    service_description: str = "Local mistake case memory API"
    api_version: str = "v1"
    auth_enabled: bool = Field(default=False, validation_alias="AUTH_ENABLED")
    data_dir: Path = Path("data")
    sync_enabled: bool = Field(default=True, validation_alias="SYNC_ENABLED")
    sync_worker_interval_seconds: float = Field(
        default=5.0,
        validation_alias="SYNC_WORKER_INTERVAL_SECONDS",
    )
    sync_worker_batch_size: int = Field(
        default=10,
        validation_alias="SYNC_WORKER_BATCH_SIZE",
    )
    sync_worker_max_retries: int = Field(
        default=5,
        validation_alias="SYNC_WORKER_MAX_RETRIES",
    )
    retrieval_api_url: str = Field(
        default="http://retrieval-api:8000",
        validation_alias="RETRIEVAL_API_URL",
    )
    retrieval_collection: str = Field(
        default="200iq_cases",
        validation_alias="RETRIEVAL_COLLECTION",
    )

    @property
    def sync_db_path(self) -> Path:
        return self.data_dir / "sync" / "jobs.sqlite3"


@lru_cache
def get_settings() -> Settings:
    return Settings()
