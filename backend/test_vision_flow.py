import urllib.request
import urllib.error
import json
import sys
import io
from typing import Any

# Cấu hình UTF-8 cho Windows Terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000/api/v1"

def http_post_json(url, data_dict, headers_dict=None) -> tuple[int, Any]:
    if headers_dict is None:
        headers_dict = {}
    headers_dict["Content-Type"] = "application/json"
    json_bytes = json.dumps(data_dict).encode("utf-8")
    req = urllib.request.Request(url, data=json_bytes, headers=headers_dict, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            return response.status, json.loads(res_body)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except:
            return e.code, err_body

def http_get(url, headers_dict=None) -> tuple[int, Any]:
    if headers_dict is None:
        headers_dict = {}
    req = urllib.request.Request(url, headers=headers_dict, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            return response.status, json.loads(res_body)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except:
            return e.code, err_body

def test_vision_and_meal_sync():
    print("=" * 70)
    print("[TEST GIAI DOAN 2] GEMINI FLASH AI CHUP ANH MON AN & DONG BO CARD 'DA NAP'")
    print("=" * 70)

    user_email = "testmobile@nutrismart.com"
    user_password = "password123"

    # 1. Đăng nhập lấy Token
    print("\n1. Dang nhap tai khoan Mobile...")
    status, body = http_post_json(f"{BASE_URL}/auth/login", {"email": user_email, "password": user_password})
    if status == 200:
        token = body["access_token"]
        print("   [OK] Dang nhap thanh cong! Nhan JWT Token.")
    else:
        print(f"   [FAIL] Dang nhap that bai: Status {status}")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Giả lập gửi ảnh lên API Phân tích Gemini Flash AI
    print("\n2. [MOBILE AI SCAN] Gia lap chup anh dia Com Tam va goi API Gemini Flash...")
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    header_part = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="com_tam.jpg"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8")
    
    dummy_jpeg = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00\x60\x00\x60\x00\x00\xFF\xD9"
    footer_part = f"\r\n--{boundary}--\r\n".encode("utf-8")
    
    body_bytes = header_part + dummy_jpeg + footer_part

    req = urllib.request.Request(
        f"{BASE_URL}/vision/analyze-meal",
        data=body_bytes,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            analyze_result = json.loads(res_body)
            print(f"   [OK] Gemini AI phan tich thanh cong:")
            print(f"      -> Mon an: {analyze_result['food_name']}")
            print(f"      -> Calo: {analyze_result['calories_kcal']} kcal")
            print(f"      -> Protein: {analyze_result['protein_g']}g | Carbs: {analyze_result['carb_g']}g | Fat: {analyze_result['fat_g']}g")
            print(f"      -> Do tin cay: {analyze_result['confidence']*100}%")
    except Exception as e:
        print(f"   [FAIL] Loi goi API Vision: {e}")
        sys.exit(1)

    # 3. Giả lập bấm nút "Lưu vào Nhật ký" trên Mobile (khẩu phần 1.0x)
    print("\n3. [MOBILE LOG] Bam nut 'Luu vao Nhat ky' (Khau phan 1.0x)...")
    log_payload = {
        "food_name": analyze_result["food_name"],
        "calories_kcal": analyze_result["calories_kcal"],
        "protein_g": analyze_result["protein_g"],
        "carb_g": analyze_result["carb_g"],
        "fat_g": analyze_result["fat_g"],
        "quantity": 1.0,
        "meal_type": "LUNCH"
    }

    status, body = http_post_json(f"{BASE_URL}/vision/log-meal", log_payload, headers)
    if status == 200:
        print(f"   [OK] Da luu bua an vao CSDL PostgreSQL:")
        print(f"      -> Thong bao: {body['message']}")
        print(f"      -> Tong Calo nap hom nay: {body['total_intake_today']} kcal")
    else:
        print(f"   [FAIL] Loi luu bua an: Status {status} - {body}")
        sys.exit(1)

    # 4. Kiểm tra dữ liệu hiển thị trên Web UI Dashboard
    print("\n4. [WEB DASHBOARD SYNC] Web goi API '/tracking/summary' de xem Card 'DA NAP' & Bieu do...")
    status, body = http_get(f"{BASE_URL}/tracking/summary?days=7", headers)
    if status == 200:
        today_summary = body[-1]
        print(f"   [OK] Du lieu hien thi tren Web Dashboard hom nay ({today_summary['day']}):")
        print(f"      CARD DA NAP: {today_summary['kcal_intake']} kcal")
        print(f"      CARD DA TIEU HAO: {today_summary['kcal_burned']} kcal")
        print(f"      CARD CON LAI: {today_summary['kcal_remaining']} kcal")
    else:
        print(f"   [FAIL] Web summary that bai: Status {status}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("SUCCESS: LUONG CHUP ANH AI -> PHAN TICH -> LUU CSDL -> DONG BO WEB HOAN HAO!")
    print("=" * 70)

if __name__ == "__main__":
    test_vision_and_meal_sync()
