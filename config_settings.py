from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    youtube_api_key: str
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"
    sentence_transformers_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    class Config:
        env_file = ".env"

settings = Settings()
