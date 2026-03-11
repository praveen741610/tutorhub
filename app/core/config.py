from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "dev"  # dev | test | prod
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/tutorhub"
    DB_FALLBACK_URL: str = "sqlite:///./tutorhub.db"
    AUTO_CREATE_TABLES: bool = True

    JWT_SECRET: str
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 14  # 14 days

    CONTACT_ALERTS_ENABLED: bool = True
    CONTACT_ALERT_EMAIL_TO: str = "praveenkumarraacharla@gmail.com"
    CONTACT_ALERT_WHATSAPP_TO: str = "+917416106610"

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "no-reply@aviacademy.com"
    SMTP_USE_TLS: bool = True

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = ""

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
