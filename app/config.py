
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Chatbot API"
    API_V1_STR: str = "/api"
    
    # DATABASE
    DATABASE_URL: str
    
    # SECURITY
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # GOOGLE GEMINI
    GOOGLE_API_KEY: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore" # Allow extra fields in .env

settings = Settings()
