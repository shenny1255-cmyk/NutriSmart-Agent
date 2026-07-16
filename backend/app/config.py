from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Trợ lý AI — Ollama chạy local
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3"
    # Giữ model trong RAM giữa các tin nhắn → tránh cold-start ở lần nhắn sau
    OLLAMA_KEEP_ALIVE: str = "30m"

    class Config:
        env_file = ".env"


settings = Settings()  # type: ignore