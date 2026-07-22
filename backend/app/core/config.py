from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Pan API"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://pan:pan@localhost:5432/pan"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24 * 7
    storage_path: str = "/data/files"
    cors_origins: str = "http://localhost:8080,http://localhost:5173"
    default_quota_bytes: int = 10 * 1024 * 1024 * 1024
    max_file_size_bytes: int = 1024 * 1024 * 1024
    share_default_days: int = 7
    recycle_retention_days: int = 30
    admin_username: str = "administrator"
    admin_initial_password: str = "123456"
    admin_email: str = "administrator@pan.internal"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
