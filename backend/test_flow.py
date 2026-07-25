import urllib.request
import urllib.error
import json
import sys
import io

# Cấu hình UTF-8 cho Windows Terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000/api/v1"

def http_post(url, data_dict, headers_dict=None):
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

def http_get(url, headers_dict=None):
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

def test_full_flow():
    print("=" * 65)
    print("[TEST] NAI NHO & DANH GIA LUONG DU LIEU TU MOBILE -> BACKEND -> WEB UI")
    print("=" * 65)

    user_email = "testmobile@nutrismart.com"
    user_password = "password123"

    # 1. Đăng ký / Đăng nhập người dùng test
    print("\n1. [MOBILE -> BE] Dang ky / Dang nhap tai khoan Mobile...")
    reg_payload = {
        "email": user_email,
        "password": user_password,
        "full_name": "Test Mobile User",
        "country_code": "VN",
        "profile": {
            "gender": "MALE",
            "birth_date": "2000-01-01",
            "height_cm": 175,
            "weight_kg": 70,
            "activity_level": 3,
            "goal": "MAINTAIN",
            "condition_ids": [],
            "allergen_ids": []
        }
    }

    status, body = http_post(f"{BASE_URL}/auth/register", reg_payload)
    if status in [201, 200]:
        token = body["access_token"]
        print("   [OK] Dang ky thanh cong! Da cap JWT Token.")
    else:
        # Nếu đã có tài khoản -> Đăng nhập
        status, body = http_post(f"{BASE_URL}/auth/login", {"email": user_email, "password": user_password})
        if status == 200:
            token = body["access_token"]
            print("   [OK] Dang nhap thanh cong! Da nhan JWT Token.")
        else:
            print(f"   [FAIL] Dang nhap that bai: Status {status} - {body}")
            sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Giả lập Mobile gửi dữ liệu đếm bước & Calo tiêu hao
    print("\n2. [MOBILE -> BE] Mobile bam nut 'Dong bo ngay' (gui 5,420 buoc & 216.8 kcal)...")
    sync_payload = {
        "steps": 5420,
        "calories_burned": 216.8,
        "distance_km": 3.93
    }
    status, body = http_post(f"{BASE_URL}/tracking/daily-activity", sync_payload, headers)
    if status == 200:
        print(f"   [OK] Backend da nhan & luu CSDL: {body}")
    else:
        print(f"   [FAIL] Gui du lieu that bai: Status {status} - {body}")
        sys.exit(1)

    # 3. Giả lập Web Frontend lấy thông tin vận động hôm nay
    print("\n3. [BE -> WEB UI] Web Frontend goi API '/tracking/today-activity'...")
    status, body = http_get(f"{BASE_URL}/tracking/today-activity", headers)
    if status == 200:
        print(f"   [OK] Du lieu tra ve cho Web Card 'Da tieu hao':")
        print(f"      -> So buoc: {body['steps']} buoc")
        print(f"      -> Calo tieu hao: {body['calories_burned']} kcal")
    else:
        print(f"   [FAIL] Web goi today-activity that bai: Status {status}")
        sys.exit(1)

    # 4. Giả lập Web Frontend lấy summary 7 ngày
    print("\n4. [BE -> WEB UI] Web Frontend goi API '/tracking/summary' cho Bieu do...")
    status, body = http_get(f"{BASE_URL}/tracking/summary?days=7", headers)
    if status == 200:
        print(f"   [OK] Du lieu tra ve cho Bieu do Web Summary (7 ngay qua):")
        for day_item in body[-3:]:
            print(f"      Date {day_item['day']}: Nap={day_item['kcal_intake']} kcal | Dot={day_item['kcal_burned']} kcal | Con lai={day_item['kcal_remaining']} kcal")
    else:
        print(f"   [FAIL] Web goi summary that bai: Status {status}")
        sys.exit(1)

    print("\n" + "=" * 65)
    print("SUCCESS: LUONG DU LIEU TU MOBILE -> BE -> CSDL -> WEB UI CHAY HOAN HAO!")
    print("=" * 65)

if __name__ == "__main__":
    test_full_flow()
