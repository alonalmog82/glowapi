import logging
import os
import pathlib
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class RootSettings(BaseSettings):
    class Config:
        case_sensitive = False
        extra = "ignore"


class LogSettings(RootSettings):
    log_level: int = Field(logging.INFO, description="Logging level (10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR)")


class AppSettings(RootSettings):
    app_host: str = Field("0.0.0.0", env="APP_HOST")
    app_port: int = Field(8080, env="APP_PORT")
    app_workers: int = Field(1, env="APP_WORKERS")
    app_reload: bool = Field(False, env="APP_RELOAD")
    app_access_logs: bool = Field(False, env="APP_ACCESS_LOGS")


class GitHubAppSettings(RootSettings):
    github_client_id: Optional[str] = Field(None, env="GITHUB_CLIENT_ID")
    github_app_installation_id: Optional[str] = Field(None, env="GITHUB_APP_INSTALLATION_ID")
    github_app_private_key: Optional[str] = Field(
        None,
        env="JWT_TOKEN",
        description="Raw PEM private key content. Newlines must be preserved (not base64).",
    )
    github_webhook_secret: Optional[str] = Field(None, env="GITHUB_WEBHOOK_SECRET")


class BitbucketSettings(RootSettings):
    bitbucket_workspace_token: Optional[str] = Field(None, env="BITBUCKET_WORKSPACE_TOKEN")
    bitbucket_webhook_secret: Optional[str] = Field(None, env="BITBUCKET_WEBHOOK_SECRET")


class Settings(AppSettings, LogSettings, GitHubAppSettings, BitbucketSettings):
    pass


def get_settings() -> Settings:
    env_file = os.getenv("CONFIG_ENV_PATH", "config.env")
    env_path = pathlib.Path(env_file)
    if env_path.exists():
        return Settings(_env_file=env_file, _env_file_encoding="utf-8")
    return Settings()
