from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
    api_key: str
    chroma_path: str = "./chroma_db"
    runbooks_path: str = "./runbooks"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_results: int = 4


settings = Settings()
