from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60

    DATABASE_URL: str

    # DigitalOcean GenAI
    DIGITALOCEAN_API_KEY: str = ""
    DIGITALOCEAN_BASE_URL: str = ""

    LLM_MODEL_ID: str = ""
    EMBED_MODEL_ID: str = ""
    RERANKER_MODEL_ID: str = ""

    COHERE_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # GCP Storage Configuration
    GOOGLE_CLOUD_PROJECT_ID: str = ""
    GOOGLE_CLOUD_STORAGE_BUCKET: str = ""
    GOOGLE_CLOUD_CREDENTIALS: str = ""


    DIGITALOCEAN_TIMEOUT_MS: int = 90000
    WEB_SEARCH_TIMEOUT_MS: int = 10000
    PGVECTOR_TIMEOUT_MS: int = 10000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_rag_config(self):
        """Warn if critical RAG environment variables are missing in production."""
        if self.ENVIRONMENT == "production":
            missing = []
            if not self.DIGITALOCEAN_API_KEY:
                missing.append("DIGITALOCEAN_API_KEY")
            if not self.DIGITALOCEAN_BASE_URL:
                missing.append("DIGITALOCEAN_BASE_URL")
            if not self.LLM_MODEL_ID:
                missing.append("LLM_MODEL_ID")
            if not self.EMBED_MODEL_ID:
                missing.append("EMBED_MODEL_ID")
            if not self.DATABASE_URL:
                missing.append("DATABASE_URL")
            if missing:
                raise ValueError(
                    f"Production RAG configuration incomplete. Missing required env vars: {', '.join(missing)}"
                )
        return self

settings = Settings()