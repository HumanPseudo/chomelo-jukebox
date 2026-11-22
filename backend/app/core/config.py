from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

WOMPI_MIN_TRANSACTION_CENTS = 150000


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
    frontend_url: str = "https://jukebox.chomelo.org"

    music_cache_ttl_seconds: int = 3600

    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # Pagos: "mock" en desarrollo sin credenciales; "stripe"/"wompi" en producción.
    payment_provider: str = "mock"
    payment_currency: str = "cop"
    wompi_sandbox: bool = False
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    wompi_public_key: str = ""
    wompi_private_key: str = ""
    wompi_events_secret: str = ""
    wompi_integrity_secret: str = ""
    wompi_payment_link: str = "https://checkout.wompi.co/l/VPOS_yJJIDR"
    cents_per_credit: int = 1500
    add_track_cooldown_seconds: int = 0
    add_track_cost_credits: int = 5

    # 5173: app de oyentes; 5174: consola de admin (orígenes separados a
    # propósito para que cada una tenga su propio localStorage/sesión).
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
    ]

    # WebSockets: pub/sub Redis para escalar entre instancias (fail-open).
    ws_pubsub_enabled: bool = True

    # Seguridad avanzada (Fase 13).
    rate_limit_global_limit: int = 300
    rate_limit_global_window: int = 60
    login_rate_limit_per_ip: int = 20
    login_rate_limit_window: int = 60

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        weak_secrets = {
            "",
            "change-me-in-prod",
            "change-me-in-production",
            "dev-secret-key-change-in-prod",
        }
        if self.environment == "production":
            if self.jwt_secret in weak_secrets or len(self.jwt_secret) < 32:
                raise ValueError(
                    "CHOMELO_JWT_SECRET debe ser aleatorio y de al menos 32 caracteres"
                )
        if self.payment_currency.lower() not in {"eur", "usd", "cop"}:
            raise ValueError("CHOMELO_PAYMENT_CURRENCY debe ser eur, usd o cop")
        return self


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
