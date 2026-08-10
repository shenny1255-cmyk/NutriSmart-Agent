# Kế hoạch Nâng cấp & Hoàn thiện Hệ thống NutriSmart Agent

Kế hoạch này bao gồm 4 hạng mục nâng cấp chiến lược giúp hoàn thiện dự án NutriSmart Agent thành một sản phẩm sẵn sàng triển khai thực tế (Production-Ready).

---

## 4 Hạng mục Nâng cấp

### Giai đoạn 1: Lịch Cào Dữ Liệu Tự Động Định Kỳ (Scheduled Auto-Scraper)
- **Mục tiêu:** Tự động cào bài viết y tế mới từ các nguồn uy tín theo lịch trình (mỗi tuần 1 lần) mà không cần Chuyên gia bấm nút thủ công.
- **Backend:**
  - Thêm dịch vụ scheduler `app/services/scheduler.py` tích hợp `APScheduler` / `asyncio` loop.
  - Tự động cào các bài viết mới từ danh sách `crawl_sources` ở trạng thái `is_active=True`.
  - Tự động tạo Notification cho Chuyên gia/Admin: "Hệ thống vừa cào N bài viết y tế mới đang chờ duyệt."

---

### Giai đoạn 2: Đánh Giá Phản Hồi AI Chat & Tab Quản Lý Phản Hồi (Chat Feedback Loop)
- **Mục tiêu:** Cho phép người dùng đánh giá Upvote / Downvote các câu trả lời của AI Trợ lý; Chuyên gia có thể xem danh sách câu trả lời bị Downvote để tinh chỉnh kho tri thức RAG.
- **Backend:**
  - Thêm trường `feedback_rating` (UPVOTE / DOWNVOTE) và `feedback_comment` vào bảng `chat_messages` trong `models.py`.
  - API `POST /api/v1/chat/messages/{message_id}/feedback`: Cho phép User đánh giá tin nhắn.
  - API `GET /api/v1/expert/chat-feedbacks`: Cho Chuyên gia xem danh sách phản hồi tiêu cực.
- **Frontend:**
  - Bổ sung nút bấm Upvote / Downvote dạng chữ thuần dưới từng tin nhắn AI trong `Chat.jsx`.
  - Thêm Tab "Phản hồi AI" trong trang `ExpertReview.jsx`.

---

### Giai đoạn 3: Xuất Báo Cáo Dinh Dưỡng PDF / Excel (Nutrition Export Report)
- **Mục tiêu:** Cho phép người dùng hoặc Chuyên gia xuất báo cáo tổng quan tiến trình 14 ngày, phân bổ calo, tỷ lệ Macro (Protein/Carb/Fat) và lịch sử cân nặng.
- **Backend:**
  - Thêm service `app/services/pdf_export.py` dùng `reportlab` / HTML template generator để sinh file PDF báo cáo dinh dưỡng sắc nét.
  - API `GET /api/v1/tracking/export-pdf`: Tải về báo cáo PDF cá nhân.
- **Frontend:**
  - Bổ sung nút "Xuất báo cáo PDF" trong giao diện Tiến trình / Dashboard.

---

### Giai đoạn 4: Đóng Gói Docker Production 1-Click (`docker-compose.prod.yml`)
- **Mục tiêu:** Đóng gói toàn bộ ứng dụng thành giải pháp 1-Click sẵn sàng deploy lên mọi VPS / Server.
- **Thành phần:**
  - `docker-compose.prod.yml`: Quản lý 4 containers (`nutrismart-db`, `nutrismart-redis`, `nutrismart-backend`, `nutrismart-frontend-nginx`).
  - `frontend/nginx.conf`: Cấu hình Nginx phục vụ ứng dụng React SPA và reverse proxy `/api/` sang Backend container.
  - `backend/Dockerfile` & `frontend/Dockerfile`: Multi-stage Dockerfile tối ưu kích thước image.

---

## Kế hoạch Kiểm thử (Verification Plan)

### Automated Tests
- Chạy unit test backend cho các endpoints mới:
  ```powershell
  cd backend
  $env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/ --capture=no
  ```

### Manual Verification
- **Test Auto-Scraper:** Kiểm tra scheduler kích hoạt cào bài viết đúng định kỳ và tạo thông báo hệ thống.
- **Test Chat Feedback:** Bấm Upvote/Downvote trong Chat, kiểm tra tab Phản hồi trên trang Expert hiển thị đúng dữ liệu.
- **Test Export PDF:** Bấm nút Xuất báo cáo, mở file PDF xem thông tin calo, biểu đồ và layout.
- **Test Docker Production:** Chạy `docker compose -f docker-compose.prod.yml up --build -d` và mở trang web trên cổng production.
