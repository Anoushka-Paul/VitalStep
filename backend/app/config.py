"""
Production configuration management for VitalStep API
Supports multiple environments and Supabase databases
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, model_validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "VitalStep API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    DEBUG: bool = False
    
    # API Configuration
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["*"]  # Configure properly for production
    
    # Primary Supabase Database
    SUPABASE_URL: str = Field(default="https://cbebmpgsbxqdzpfgqulj.supabase.co")
    SUPABASE_ANON_KEY: str
    
    # Secondary Supabase Database (for multi-database support)
    SUPABASE_URL_2: Optional[str] = None
    SUPABASE_ANON_KEY_2: Optional[str] = None
    
    # HubSpot Integration
    HUBSPOT_PAT: str
    
    # ML Model Configuration
    MODEL_PATH: str = Field(default="../ml/artifacts")
    MODEL_VERSION: str = "latest"
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    API_KEY_HEADER: str = "X-API-Key"
    
    @model_validator(mode="before")
    @classmethod
    def parse_env_vars(cls, values):
        """Parse environment variables before validation"""
        if isinstance(values, dict):
            cors = values.get("CORS_ORIGINS")
            if isinstance(cors, str):
                if cors.strip() == "*":
                    values["CORS_ORIGINS"] = ["*"]
                else:
                    values["CORS_ORIGINS"] = [origin.strip() for origin in cors.split(",") if origin.strip()]
        return values
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }


# Global settings instance
settings = Settings()