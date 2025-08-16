from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Management Accounting"
    APP_URL: str = "http://localhost:8080"
    DATABASE_URL: str
    REDIS_URL: str
    NEXTAUTH_SECRET: str = "change_me"
    PDF_MAX_MB: int = 20

settings = Settings()
