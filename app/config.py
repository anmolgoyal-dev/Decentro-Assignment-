import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Expense Sharing Service"
    debug: bool = False
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./expense_sharing.db"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
