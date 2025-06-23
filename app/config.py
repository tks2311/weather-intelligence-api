import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENWEATHER_API_KEY: str = "your_openweather_api_key_here"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()