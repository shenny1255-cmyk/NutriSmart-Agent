import sys
import io
import os
from app.config import settings
from google import genai

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("=" * 60)
print("📋 DANH SÁCH CÁC MODEL KHẢ DỤNG CHO API KEY CỦA BẠN:")
print("=" * 60)

try:
    models = client.models.list()
    for m in models:
        if "flash" in m.name.lower() or "gemini" in m.name.lower(): # type: ignore
            print(f"  • {m.name}")
except Exception as e:
        print(f"Lỗi: {e}")
