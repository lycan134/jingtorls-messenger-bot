
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    meta_verify_token: str = ""
    meta_page_access_token: str = ""
    meta_app_secret: str = ""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
