from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://tender:tender_hack_2026@localhost:5432/tender_search"
    redis_url: str = "redis://localhost:6379/0"
    embedding_model: str = "cointegrated/rubert-tiny2"
    embedding_dim: int = 312  # rubert-tiny2 output dimension
    search_top_k: int = 50
    final_top_k: int = 20
    bm25_weight: float = 0.4
    semantic_weight: float = 0.6
    personalization_boost: float = 0.3
    negative_signal_decay: float = 0.8
    symspell_max_distance: int = 2

    model_config = {"env_prefix": "", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    return Settings()
