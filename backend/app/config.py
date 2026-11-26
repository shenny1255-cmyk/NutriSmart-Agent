from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    APP_ENV: str = "development"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # CORS configuration: danh sách domain frontend phân cách bởi dấu phẩy
    # Ví dụ: "https://my-app.vercel.app,http://localhost:5173"
    CORS_ORIGINS: str = ""
    ALLOWED_EMAIL_DOMAINS: str = ""

    # Gemini Flash AI Key
    GEMINI_API_KEY: str = ""

    # AI Provider Adapter (services/llm.py) - GĐ1 ĐATN
    # "ollama": tự host, dữ liệu không rời máy chủ (mặc định) · "gemini": cloud, client không cần Ollama
    LLM_PROVIDER: str = "ollama"
    # Cloud lỗi/hết quota → tự chuyển sang Ollama nội bộ
    LLM_FALLBACK_LOCAL: bool = True
    GEMINI_CHAT_MODEL: str = "gemini-3.5-flash-lite"
    # Giới hạn token đầu ra mặc định cho cloud khi caller không chỉ định
    LLM_MAX_OUTPUT_TOKENS: int = 1024

    # Trợ lý AI - Ollama chạy local
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3"
    OLLAMA_CHAT_MODEL: str = "gemma3:1b"
    OLLAMA_EMBEDDING_MODEL: str = "bge-m3"
    OLLAMA_KEEP_ALIVE: str = "30m"
    # Giới hạn token mỗi câu trả lời chat; 250 làm câu trả lời dài (thực đơn theo bữa) bị cắt cụt
    OLLAMA_CHAT_NUM_PREDICT: int = 700

    # Sinh lộ trình 7 ngày bằng LLM - JSON dài, máy yếu có thể mất 3-5 phút
    PLAN_LLM_TIMEOUT_SECONDS: float = 420.0

    # Job check-in 14 ngày: reconcile kỳ quá hạn và sinh feedback đang chờ.
    PLAN_CHECKIN_INTERVAL_MINUTES: int = 30
    PLAN_CHECKIN_DELAY_SECONDS: int = 60
    # Tương thích code cũ; job đánh giá 7 ngày đã bị vô hiệu hóa.
    PLAN_EVAL_INTERVAL_MINUTES: int = 0
    PLAN_EVAL_DELAY_SECONDS: int = 60

    # App chỉ tự tick mục vận động khi kcal thiết bị đạt ít nhất ngưỡng này.
    MOBILE_EXERCISE_MIN_KCAL: float = 350.0

    # Xác minh email - SMTP (để trống SMTP_HOST → ghi link ra console thay vì gửi thật)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "NutriSmart <no-reply@nutrismart.local>"

    # Chống lạm dụng mã PIN đăng ký (spam email, dò mã)
    PIN_SENDS_PER_EMAIL_PER_HOUR: int = 5
    PIN_SENDS_PER_IP_PER_HOUR: int = 10
    # Chỉ bật khi backend đứng sau reverse proxy tin cậy; nếu không, X-Forwarded-For có thể bị giả mạo
    TRUST_PROXY_HEADERS: bool = False
    APP_BASE_URL: str = "http://localhost:5173"   # gốc cho link xác minh

    class Config:
        env_file = ".env"
        # Bỏ qua biến lạ trong .env thay vì crash - .env thường mang thêm key của
        # nhánh khác (ví dụ SMTP_*), không nên làm backend không khởi động được.
        extra = "ignore"


settings = Settings()  # type: ignore
