"""Configuration management for Smart Info Navigator MCP Server."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server Configuration
    app_name: str = "Workflow Orchestrator MCP"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    public_base_url: str = "http://localhost:8000"

    # Database Configuration (PostgreSQL)
    # Using port 5433 to avoid conflict with local PostgreSQL on 5432
    database_url: str = "postgresql+asyncpg://workflow_user:workflow_password@localhost:5433/workflow_orchestrator"
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Email Configuration (SMTP)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True

    # Redis Configuration
    # Using port 6380 to avoid conflict with local Redis on 6379
    redis_url: str = "redis://localhost:6380"
    redis_db: int = 0
    session_ttl: int = 86400  # 24 hours in seconds
    cache_ttl: int = 3600  # 1 hour in seconds

    # OAuth Configuration
    oauth_enabled: bool = False  # Set to True to enable OAuth protection on MCP endpoints
    oauth_issuer: str = "http://localhost:8000"  # Will be overridden by public_base_url in production
    jwt_secret: str  # Required: Must be at least 32 characters for HS256
    jwt_algorithm: str = "RS256"  # Use RS256 for production (asymmetric), HS256 for dev
    jwt_private_key_path: Optional[str] = None  # Path to RSA private key for RS256
    jwt_public_key_path: Optional[str] = None  # Path to RSA public key for RS256
    access_token_expire_minutes: int = 60  # 1 hour as per ChatGPT Apps recommendation
    refresh_token_expire_days: int = 30  # 30 days
    authorization_code_expire_minutes: int = 10  # 10 minutes for auth codes

    # CORS Configuration
    allowed_origins: str = "https://chat.openai.com,https://chatgpt.com"
    allowed_hosts: str = ""  # Comma-separated extra hosts for DNS rebinding protection

    # OpenAI Apps domain verification
    openai_apps_verification_token: Optional[str] = None
    openai_apps_verification_path: str = "/.well-known/openai-apps-challenge"

    # Demo login for App review
    demo_username: Optional[str] = None
    demo_password: Optional[str] = None
    demo_session_ttl_minutes: int = 60

    # Rate Limiting
    rate_limit_per_minute: int = 100
    rate_limit_burst: int = 20

    # Export Configuration
    max_export_size_mb: int = 10
    export_temp_dir: str = "/tmp/smart-info-navigator"

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "text"  # "text" or "json"
    log_output: str = "stdout"  # "stdout", "file", "both"
    log_file_path: str = "/var/log/workflow-orchestrator/app.log"
    log_max_bytes: int = 10485760  # 10MB
    log_backup_count: int = 5

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse allowed origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def allowed_hosts_list(self) -> list[str]:
        """Parse allowed hosts from comma-separated string."""
        if not self.allowed_hosts:
            return []
        return [host.strip() for host in self.allowed_hosts.split(",")]


# Global settings instance
settings = Settings()
