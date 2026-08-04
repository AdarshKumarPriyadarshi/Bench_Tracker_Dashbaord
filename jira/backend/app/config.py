from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jira_base_url: str = "https://mercedes-benz.atlassian.net"
    jira_user_email: str
    jira_api_token: str

    cache_ttl_seconds: int = 300
    sync_interval_seconds: int = 60

    app_port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
