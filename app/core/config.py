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

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
