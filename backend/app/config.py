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

    # Xác minh email — SMTP (để trống SMTP_HOST → ghi link ra console thay vì gửi thật)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "NutriSmart <no-reply@nutrismart.local>"
    APP_BASE_URL: str = "http://localhost:5173"   # gốc cho link xác minh

    class Config:
        env_file = ".env"


settings = Settings()  # type: ignore