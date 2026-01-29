"""Application configuration using Pydantic Settings.

This module provides centralized configuration management with:
- Environment variable loading
- Type validation
- Default values
- Configuration validation
"""

import os
from pathlib import Path
from typing import Optional, Literal
import logging
import json
from pydantic import (
    Field,
    field_validator,
    PostgresDsn,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

def get_env_file():
    env_router_file = Path(__file__).parent.parent / ".env"
    if env_router_file.exists():
        with env_router_file.open() as f:
            env_file_name = f.read().strip()
            env_file = Path(__file__).parent.parent / env_file_name
            if env_file.exists():
                return env_file
            else:
                msg = f"Environment file {env_file_name} not found, create it in the project root."
                raise FileNotFoundError(msg)
    else:
        logger.warning("Environment router file not found, create .env file and place name of env file in it e.g .env.development")


class Settings(BaseSettings):
    """Application settings with Pydantic validation.
    
    All settings are loaded from environment variables or .env file.
    Type validation and conversion is handled automatically.
    """

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        # env_file=get_env_file() if get_env_file() else None,
        env_file_encoding="utf-8",
        case_sensitive=True,
        # Allow extra fields from environment
        extra="ignore",
    )

    # ==================== Application Settings ====================
    PYTHON_ENV: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )

    # ==================== Database Settings ====================
    DB_URL: PostgresDsn = Field(
        description="Database connection URL (PostgreSQL)"
    )

    DB_SECRET_KEY: str = Field(
        default="default_key_32_bytes_long!!",
        description="Database encryption key (must be 32 bytes)"
    )

    USE_DEV_DB: bool = Field(
        default=False,
        description="Use development database mode"
    )

    WRITE_POOL_SIZE: int = Field(
        default=5,
        description="Database write pool size"
    )

    # ==================== Telegram Bot Settings ====================
    BOT_TOKEN: str = Field(
        description="Telegram bot token from @BotFather"
    )
    
    # Telegram Userbot (Telethon)
    TELEGRAM_API_ID: Optional[int] = Field(
        default=None,
        description="Telegram API ID for userbot"
    )

    TELEGRAM_API_HASH: Optional[str] = Field(
        default=None,
        description="Telegram API Hash for userbot"
    )

    TELEGRAM_SESSION_NAME: str = Field(
        default="bt6_parser",
        description="Telethon session name"
    )

    # ==================== AI Parser Settings ====================
    OPENROUTER_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key for AI parser (future feature)"
    )

    # ==================== Computed Properties ====================
    @property
    def PROJECT_ROOT(self) -> Path:
        """Get project root directory."""
        return Path(__file__).parent.parent

    @property
    def ALEMBIC_INI_PATH(self) -> str:
        """Path to alembic.ini."""
        return str(self.PROJECT_ROOT / "alembic.ini")

    @property
    def ALEMBIC_SCRIPT_PATH(self) -> str:
        """Path to alembic migrations directory."""
        return str(self.PROJECT_ROOT / "src" / "database" / "migrations")

    @property
    def database_url(self) -> URL:
        """Get SQLAlchemy database URL object."""    
        return make_url(str(self.DB_URL))

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.PYTHON_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.PYTHON_ENV == "development"

    # ==================== Validators ====================
    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is uppercase."""
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("PYTHON_ENV", mode="before")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate and normalize environment name."""
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator("DB_SECRET_KEY", mode="after")
    @classmethod
    def validate_db_secret_key(cls, v: str) -> str:
        """Validate DB secret key length."""
        if len(v.encode('utf-8')) < 32:
            raise ValueError("DB_SECRET_KEY must be at least 32 bytes long")
        return v

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        """Validate settings and perform post-init setup."""
        # Validate BOT_TOKEN is provided
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        
        return self


class CustomRailwayLogFormatter(logging.Formatter):
    """Custom JSON formatter for logging (Railway-compatible)."""
    
    def format(self, record):
        log_record = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def get_logger():
    """Get configured logger instance."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add new handler with custom formatter
    handler = logging.StreamHandler()
    formatter = CustomRailwayLogFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


# Create global config instance
Config = Settings()

# Create global logger instance
logger = get_logger()


# Backward compatibility function
def get_settings() -> Settings:
    """Get settings instance (singleton pattern for backward compatibility)."""
    return Config
