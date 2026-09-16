from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CHOMELO_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "Chomelo Jukebox API"
    environment: str = "development"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://chomelo:chomelo@db:5432/chomelo"
    redis_url: str = "redis://redis:6379/0"
    worker_url: str = "http://worker:9000"

    music_cache_ttl_seconds: int = 3600

    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # Pagos: "mock" en desarrollo sin credenciales; "stripe" en producción.
    payment_provider: str = "mock"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    cents_per_credit: int = 10

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
