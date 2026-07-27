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

    # Sinh lộ trình 7 ngày bằng LLM — JSON dài, máy yếu có thể mất 3–5 phút
    PLAN_LLM_TIMEOUT_SECONDS: float = 420.0

    # Job đánh giá lộ trình 7 ngày — 0 phút = tắt job nền (vẫn chạy tay qua API)
    PLAN_EVAL_INTERVAL_MINUTES: int = 360
    PLAN_EVAL_DELAY_SECONDS: int = 60      # hoãn lần quét đầu để backend khởi động xong

    # Xác minh email — SMTP (để trống SMTP_HOST → ghi link ra console thay vì gửi thật)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "NutriSmart <no-reply@nutrismart.local>"
    APP_BASE_URL: str = "http://localhost:5173"   # gốc cho link xác minh

    class Config:
        env_file = ".env"
        # Bỏ qua biến lạ trong .env thay vì crash — .env thường mang thêm key của
        # nhánh khác (ví dụ SMTP_*), không nên làm backend không khởi động được.
        extra = "ignore"


settings = Settings()  # type: ignore