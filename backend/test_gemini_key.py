import os

from app.config import settings
from app.services.gemini_vision import GEMINI_VISION_MODELS
from google import genai

def check_key():
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    for model_name in GEMINI_VISION_MODELS:
        print(f"\n🔄 Thử model '{model_name}'...")
        try:
            res = client.models.generate_content(
                model=model_name,
                contents="Hello, reply with 'OK' if working."
            )
            print(f"   ✅ MODEL '{model_name}' THÀNH CÔNG VỚI API KEY CỦA BẠN!")
            print(f"   👉 Phản hồi: {(res.text or '').strip()}")
            return model_name
        except Exception as e:
            print(f"   ❌ Lỗi {model_name}: {e}")

if __name__ == "__main__":
    check_key()
