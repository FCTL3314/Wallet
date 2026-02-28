from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Wallet"
    API_PREFIX: str = "/api"

    DATABASE_URL: str = "postgresql+asyncpg://wallet:wallet@localhost:5432/wallet"

    CORS_ORIGINS: list[str] = []

    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
