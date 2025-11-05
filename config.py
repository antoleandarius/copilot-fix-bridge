"""
Configuration management using Pydantic Settings.
Centralizes all environment variables and provides validation.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application configuration with environment variable support"""

    # GitHub Configuration
    github_token: str
    github_repo: str

    # JIRA Configuration
    jira_base_url: str
    jira_email: str
    jira_api_token: str

    # AgentHQ Configuration
    agenthq_api_key: Optional[str] = None
    agenthq_base_url: str = "https://api.agenthq.dev"
    agenthq_agent_id: Optional[str] = None
    agenthq_webhook_url: Optional[str] = None
    agenthq_mock_mode: bool = True
    agenthq_timeout: int = 30

    # Security
    webhook_secret: Optional[str] = None

    # Application Settings
    port: int = 8000
    log_level: str = "INFO"
    json_logs: bool = False

    # Feature Flags
    enable_agenthq: bool = False
    fallback_to_github_actions: bool = True

    # Retry Configuration
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    retry_initial_delay: float = 1.0

    class Config:
        env_file = ".env"
        case_sensitive = False
        # Allow environment variables to override .env file
        env_file_encoding = "utf-8"

    def validate_agenthq_config(self) -> bool:
        """Validate AgentHQ configuration is complete"""
        if not self.enable_agenthq:
            return True

        if self.agenthq_mock_mode:
            return True

        # For real API, require all fields
        required_fields = [
            self.agenthq_api_key,
            self.agenthq_agent_id,
            self.agenthq_webhook_url
        ]

        return all(required_fields)


# Global settings instance
settings = Settings()
