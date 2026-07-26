from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Gemini Flash AI Key
    GEMINI_API_KEY: str = ""

    # Trợ lý AI — Ollama chạy local
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3"
    OLLAMA_EMBEDDING_MODEL: str = "bge-m3"
    OLLAMA_KEEP_ALIVE: str = "30m"

    class Config:
        env_file = ".env"
        # Bỏ qua biến lạ trong .env thay vì crash — .env thường mang thêm key của
        # nhánh khác (ví dụ SMTP_*), không nên làm backend không khởi động được.
        extra = "ignore"


settings = Settings()  # type: ignore