import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.config import settings
from google import genai

def test_key():
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)

    models_to_test = [
        "gemini-2.0-flash-lite",
        "gemini-flash-latest",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash-001",
    ]

    for model_name in models_to_test:
        print(f"\n🔄 Thử model '{model_name}'...")
        try:
            res = client.models.generate_content(
                model=model_name,
                contents="Hello, reply with 'OK' if working."
            )
            print(f"   ✅ MODEL '{model_name}' THÀNH CÔNG VỚI API KEY CỦA BẠN!")
            print(f"   👉 Phản hồi: {res.text.strip()}")
            return model_name
        except Exception as e:
            print(f"   ❌ Lỗi {model_name}: {e}")

if __name__ == "__main__":
    test_key()
