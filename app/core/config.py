from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://quiz:quiz@localhost:5432/quiz"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "test-secret-key"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


settings = Settings()
