from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://heimdall:heimdall@localhost:5432/heimdall"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth / JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # App
    APP_NAME: str = "Heimdall API"
    API_V1_PREFIX: str = "/api/v1"

    # Uploads
    UPLOAD_DIR: str = "uploads"

    # Holiday API
    HOLIDAY_API_BASE_URL: str = "https://openholidaysapi.org"
    HOLIDAY_COUNTRY: str = "DE"
    HOLIDAY_SUBDIVISION: str = "DE-BW"


settings = Settings()
