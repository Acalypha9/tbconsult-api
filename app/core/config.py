from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    
    DATABASE_URL: str
    REDIS_URL: str
    
    # DigitalOcean GenAI
    DIGITALOCEAN_API_KEY: str = ""
    DIGITALOCEAN_BASE_URL: str = ""
    
    LLM_MODEL_ID: str = ""
    EMBED_MODEL_ID: str = ""
    
    COHERE_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    
    RATE_LIMIT_PER_MINUTE: int = 10
    
    DIGITALOCEAN_TIMEOUT_MS: int = 15000
    WEB_SEARCH_TIMEOUT_MS: int = 1500
    PGVECTOR_TIMEOUT_MS: int = 2000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()