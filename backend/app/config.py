"""
Production configuration management for VitalStep API
Supports multiple environments and Supabase databases
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "VitalStep API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", regex="^(development|staging|production)$")
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
    LOG_LEVEL: str = Field(default="INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production")
    API_KEY_HEADER: str = "X-API-Key"
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()