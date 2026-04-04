from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://wallet:wallet@localhost:5432/wallet"
    REDIS_URL: str = "redis://localhost:6379/0"
    REPORTS_DIR: str = "/reports"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
