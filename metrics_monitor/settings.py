from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )

    pool_min_size: int = 10
    pool_max_size: int = 10

    semaphore_max_concurrent: int = 10
