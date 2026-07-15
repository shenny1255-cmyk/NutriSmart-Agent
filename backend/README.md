# NutriSmart Agent Backend API

Mã nguồn dịch vụ Backend cho dự án NutriSmart Agent, được phát triển bằng **FastAPI**, **SQLAlchemy** và kết nối tới database PostgreSQL.

---

## 🛠️ Yêu cầu chuẩn bị
* Python 3.10+
* Docker & Docker Compose (dành cho cơ sở dữ liệu)

---

## 🚀 Hướng dẫn cài đặt và chạy ứng dụng

### Bước 1: Khởi động Cơ sở dữ liệu & Cache (Docker)
Di chuyển vào thư mục `db` ở thư mục gốc của dự án và chạy lệnh sau để khởi động PostgreSQL (với pgvector) và Redis:
```bash
cd db
docker compose up -d
```
*Lưu ý: Docker sẽ tự động chạy các tệp migrations trong `db/migrations` để khởi tạo các bảng và chèn dữ liệu mẫu.*

### Bước 2: Thiết lập môi trường ảo Python
Quay lại thư mục `backend` và khởi tạo môi trường ảo:
```bash
cd ../backend
python -m venv .venv
```

Kích hoạt môi trường ảo:
* **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
* **Windows (CMD):**
  ```cmd
  .\.venv\Scripts\activate.bat
  ```
* **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

### Bước 3: Cài đặt các thư viện phụ thuộc
Sau khi kích hoạt môi trường ảo, tiến hành cài đặt các package trong `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Bước 4: Cấu hình biến môi trường
Tạo tệp `.env` tại thư mục gốc của `backend` với nội dung cấu hình như sau (đã được cấu hình tự động cho môi trường chạy local):
```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/nutrismart
SECRET_KEY=doi-chuoi-nay-thanh-cai-gi-do-ngau-nhien-that-dai
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### Bước 5: Khởi chạy ứng dụng Backend
Chọn 1 trong 2 cách sau:

* **Cách 1 (Đã kích hoạt môi trường ảo `.venv`):**
  ```bash
  python -m uvicorn app.main:app --reload
  ```
* **Cách 2 (Chạy trực tiếp, không cần kích hoạt `.venv` trước):**
  ```bash
  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
  ```

---

## 📝 Tài liệu API (Interactive API Docs)
Khi server đã chạy thành công tại cổng 8000, bạn có thể truy cập tài liệu API trực tiếp qua trình duyệt:
* Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
* ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
