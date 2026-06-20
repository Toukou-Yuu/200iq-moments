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


@lru_cache
def get_settings() -> Settings:
    return Settings()
