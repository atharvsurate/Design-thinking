from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "SIH26190 Legal DMS API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "securepassword"
    POSTGRES_DB: str = "legal_dms"
    
    # Keycloak
    KEYCLOAK_SERVER_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "mha-legal-docs"
    KEYCLOAK_CLIENT_ID: str = "fastapi-client"
    
    # Vault
    VAULT_URL: str = "http://localhost:8200"
    VAULT_TOKEN: str = "root"

    # MinIO
    MINIO_URL: str = "localhost:9000"
    MINIO_ROOT_USER: str = "admin"
    MINIO_ROOT_PASSWORD: str = "securepassword"

    @property
    def sync_database_uri(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    @property
    def async_database_uri(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

settings = Settings()
