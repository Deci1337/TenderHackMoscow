from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "TenderHack Smart Search"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://tenderhack:tenderhack_secret@localhost:5432/tenderhack"
    REDIS_URL: str = "redis://localhost:6379/0"
    DATA_DIR: str = "./data"

    EMBEDDING_DIM: int = 312

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
