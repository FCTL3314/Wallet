from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://wallet:wallet@localhost:5432/wallet"
    KAFKA_URL: str = "localhost:9092"
    REPORTS_DIR: str = "/reports"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
