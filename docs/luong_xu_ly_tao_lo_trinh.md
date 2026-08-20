# TÀI LIỆU THIẾT KẾ KIẾN TRÚC & LUỒNG XỬ LÝ
## TÍNH NĂNG: XÁC NHẬN & CẬP NHẬT CHỈ SỐ KHI TẠO LỘ TRÌNH MỚI (PLAN RECREATION FLOW)
**Dự án:** NutriSmart Agent
**Tác giả:** Nhóm E15
**Ngày cập nhật:** 20/08/2026

---

## 1. Mục tiêu & Ý nghĩa thiết kế

1. **Bảo vệ dữ liệu người dùng (Data Loss Prevention):**
   - Ngăn ngừa tình trạng người dùng vô tình bấm nút *"Tạo lộ trình mới"* làm gián đoạn hoặc ghi đè lộ trình 7 ngày đang thực hiện.
2. **Hiệu chuẩn thể trạng động (Dynamic Profile Calibration):**
   - Lộ trình dinh dưỡng được tối ưu hóa dựa trên chỉ số thể trạng thực tế. Khi bắt đầu chu kỳ mới, việc cập nhật lại **Cân nặng** và **Chiều cao** giúp thuật toán tính lại chính xác BMR (Mifflin-St Jeor), TDEE và Calorie Target.
3. **Rào chắn an toàn y tế (10% Weight Delta Guardrail):**
   - Biến động cân nặng quá $10\%$ trong một chu kỳ ngắn thường do lỗi gõ nhầm (typo) hoặc sụt/tăng cân bệnh lý bất thường. Việc giới hạn và cảnh báo giúp bảo vệ người dùng và đảm bảo tính an toàn của hệ thống.

---

## 2. Sơ đồ Luồng Hoạt Động (Activity Flowchart)

```mermaid
flowchart TD
    Start(["Người dùng bấm 'Tạo lộ trình mới'"]) --> CheckPlan{"Người dùng đã có<br/>lộ trình ACTIVE?"}

    CheckPlan -- "Chưa có (Lần đầu)" --> DirectGen["Sinh lộ trình ngay từ hồ sơ gốc"]

    CheckPlan -- "Đã có lộ trình" --> OpenModal["Hiển thị Modal Xác nhận &<br/>Cập nhật chỉ số thể trạng"]

    OpenModal --> FillForm["Hiển thị Form (Pre-fill giá trị cũ):<br/>- Chiều cao (cm)<br/>- Cân nặng mới (kg)<br/>- Giới hạn hợp lệ (±10%)"]

    FillForm --> UserInput["Người dùng nhập Cân nặng & Chiều cao mới"]

    UserInput --> Validate{"Kiểm tra điều kiện:<br/>0.9 * W_cũ ≤ W_mới ≤ 1.1 * W_cũ"}

    Validate -- "Vi phạm (> 10%)" --> ShowWarning["- Hiển thị thông báo đỏ cảnh báo lệch > 10%<br/>- Vô hiệu hóa nút 'Xác nhận'<br/>- Gợi ý cập nhật tại trang Hồ sơ"]
    ShowWarning --> UserInput

    Validate -- "Hợp lệ (≤ 10%)" --> EnableBtn["Kích hoạt nút 'Xác nhận & Bắt đầu tạo'"]

    EnableBtn --> Submit(["Người dùng bấm Xác nhận"])

    Submit --> CallAPI1["Gọi PUT /api/v1/auth/me:<br/>- Lưu BodyMetricHistory mới<br/>- Tính lại TDEE & Daily Calorie Target"]

    CallAPI1 --> CallAPI2["Gọi POST /api/v1/plans/generate:<br/>- Đưa tác vụ vào hàng đợi nền (Job Queue)"]

    CallAPI2 --> Worker["Worker nền:<br/>1. Chuyển Plan cũ sang trạng thái 'REVISED'<br/>2. Gọi AI (Ollama gemma3) sinh thực đơn 7 ngày<br/>3. Khởi tạo chu kỳ Checkin mới"]

    Worker --> Complete(["Hoàn tất: Hiển thị Lộ trình cá nhân hóa mới"])
```

---

## 3. Sơ đồ Tuần tự Hệ thống (Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as Frontend (React / Plan.jsx)
    participant API as Backend (FastAPI)
    participant DB as Database (PostgreSQL)
    participant AI as Local AI (Ollama gemma3)

    User->>UI: Bấm "Tạo lộ trình mới"
    UI->>UI: Kiểm tra có plan.active hiện tại
    UI-->>User: Mở Popup Modal Xác nhận & Form chỉ số

    User->>UI: Nhập Chiều cao (cm) & Cân nặng mới (kg)
    UI->>UI: Validate realtime (|W_mới - W_cũ| / W_cũ <= 0.10)

    User->>UI: Bấm "Xác nhận & Tạo lộ trình"
    UI->>API: PUT /api/v1/auth/me (height_cm, weight_kg)
    API->>DB: Ghi BodyMetricHistory & Cập nhật Profile
    API->>API: Tính lại Mifflin-St Jeor BMR & TDEE
    API-->>UI: 200 OK (Profile cập nhật thành công)

    UI->>API: POST /api/v1/plans/generate
    API->>API: Enqueue Job sinh lộ trình
    API-->>UI: 202 Accepted (job_id)

    loop Polling trạng thái Job (mỗi 3s)
        UI->>API: GET /api/v1/plans/generate/{job_id}
        Note over API,AI: Worker chạy ngầm: Plan cũ -> REVISED
        API->>AI: Prompt thực đơn 7 ngày + bài tập theo TDEE mới
        AI-->>API: Trả về JSON 7 ngày
        API->>DB: Lưu NutritionPlan mới (version + 1) & tạo Checkin
        API-->>UI: Trả về trạng thái DONE
    end

    UI->>API: GET /api/v1/plans/active
    API-->>UI: Dữ liệu lộ trình mới (version n+1)
    UI-->>User: Hiển thị giao diện lộ trình dinh dưỡng mới
```

---

## 4. Đặc tả Công thức & Ràng buộc Kiểm tra (Validation Rules)

### 4.1. Quy tắc giới hạn cân nặng $\pm 10\%$
Gọi $W_{cũ}$ là cân nặng ghi nhận gần nhất, $W_{mới}$ là cân nặng người dùng vừa nhập:

$$\Delta W = |W_{mới} - W_{cũ}|$$

Điều kiện hợp lệ:
$$\frac{\Delta W}{W_{cũ}} \le 0.10 \iff 0.90 \times W_{cũ} \le W_{mới} \le 1.10 \times W_{cũ}$$

*Ví dụ minh họa:*
- Cân nặng gần nhất $W_{cũ} = 70.0\text{ kg}$.
- Khoảng cho phép: $[70 \times 0.9, 70 \times 1.1] = [63.0\text{ kg}, 77.0\text{ kg}]$.
- Nếu nhập $60.0\text{ kg}$ (giảm $14.3\%$) $\rightarrow$ **Cảnh báo lỗi, khóa nút gửi.**

---

### 4.2. Công thức tính lại Năng lượng tiêu chuẩn (Mifflin-St Jeor)

1. **Chỉ số trao đổi chất cơ bản (BMR):**
   $$\text{BMR} = 10 \times W_{mới} + 6.25 \times H_{mới} - 5 \times \text{Tuổi} + S$$
   *Trong đó:* $S = +5$ (Nam) hoặc $S = -161$ (Nữ).

2. **Tổng năng lượng tiêu hao hàng ngày (TDEE):**
   $$\text{TDEE} = \text{BMR} \times \text{Activity\_Multiplier}$$

3. **Lượng Calo mục tiêu (Target Kcal):**
   - Giảm cân (`LOSE_WEIGHT`): $\text{Target} = \text{TDEE} - 500\text{ kcal}$
   - Tăng cơ (`GAIN_MUSCLE`): $\text{Target} = \text{TDEE} + 300\text{ kcal}$
   - Giữ cân (`MAINTAIN`): $\text{Target} = \text{TDEE}$

---

## 5. Đặc tả Giao diện Modal (UI Specification)

### Các thành phần chính trong Modal:
1. **Tiêu đề:** *"Xác nhận tạo lộ trình dinh dưỡng mới"*
2. **Cảnh báo tiến trình:** *"Lộ trình hiện tại sẽ được lưu trữ. Hệ thống sẽ tối ưu hóa lộ trình 7 ngày tiếp theo dựa trên thể trạng mới nhất của bạn."*
3. **Trường nhập liệu:**
   - **Chiều cao (cm):** Input dạng số nguyên/thập phân (min: 50, max: 250).
   - **Cân nặng hiện tại (kg):** Input số (min: 20, max: 300, bước nhảy 0.1).
   - **Gợi ý khoảng an toàn:** Hiển thị nhãn nhỏ màu xám dưới ô cân nặng: `(Khoảng hợp lệ: 63.0 kg - 77.0 kg)`.
4. **Trạng thái cảnh báo vi phạm:**
   - Text lỗi màu đỏ cam khi nhập ngoài khoảng 10%:
     *"Cân nặng thay đổi hơn 10% so với lần ghi nhận gần nhất (70.0 kg). Nếu có sự thay đổi lớn, vui lòng cập nhật tại trang Hồ sơ."*
5. **Nút thao tác:**
   - **Hủy bỏ (Cancel):** Đóng modal, giữ nguyên màn hình cũ.
   - **Xác nhận & Tạo lộ trình (Confirm):** Nút chính (primary), chỉ bật khi input hợp lệ.
