from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    LLM_PROVIDER: Literal["openai", "anthropic"] = "openai"
    LLM_MODEL: str = "gpt-4-turbo-preview"

    # External APIs
    IMD_API_KEY: str | None = None
    IMD_API_BASE: str = "https://api.imd.gov.in/api/v1"
    GDACS_API_URL: str = "https://www.gdacs.org/gdacsapi/api/Events/geteventlist/latest"
    MOSDAC_API_KEY: str | None = None
    MOSDAC_API_URL: str | None = None
    ROUTING_PROVIDER: Literal["simulation", "osrm"] = "simulation"
    OSRM_BASE_URL: str | None = None
    DATA_MODE: str = "simulation"
    GDACS_MODE: str | None = None
    IMD_MODE: str | None = None
    MOSDAC_MODE: str | None = None
    ROUTING_MODE: str | None = None

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:3000"
    SSE_ENABLED: str = "true"

    # Security
    SECRET_KEY: str = "dev-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
