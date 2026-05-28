from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    chroma_path: str = "./chroma_db"
    runbooks_path: str = "./runbooks"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_results: int = 4

    class Config:
        env_file = ".env"


settings = Settings()
