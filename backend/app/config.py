from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "TenderHack Smart Search"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database (Dev1)
    DATABASE_URL: str = "postgresql+asyncpg://tenderhack:tenderhack_secret@localhost:5432/tenderhack"
    REDIS_URL: str = "redis://localhost:6379/0"
    DATA_DIR: str = "./data"

    # ML / Embeddings (Dev2)
    EMBEDDING_MODEL: str = "cointegrated/rubert-tiny2"
    EMBEDDING_DIM: int = 312
    SEARCH_TOP_K: int = 50
    FINAL_TOP_K: int = 20
    BM25_WEIGHT: float = 0.4
    SEMANTIC_WEIGHT: float = 0.6
    PERSONALIZATION_BOOST: float = 0.3
    NEGATIVE_SIGNAL_DECAY: float = 0.8
    SYMSPELL_MAX_DISTANCE: int = 2

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


@lru_cache
def get_settings() -> Settings:
    return settings
