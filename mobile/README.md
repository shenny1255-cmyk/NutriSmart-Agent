# NutriSmart Agent - Mobile Application (React Native Expo)

Ứng dụng di động hỗ trợ theo dõi vận động thời gian thực, đếm bước chân ngầm, phân tích dinh dưỡng đĩa thức ăn bằng AI Gemini Flash 2.0 và đồng bộ trực tiếp với CSDL PostgreSQL & Web Dashboard.

---

## Các Tính Năng Nổi Bật Trên Mobile

### 1. Đếm bước chân ngầm & Calo tiêu hao (Step Tracker)
- Cảm biến kép (Pedometer + Accelerometer): Tự động đếm bước chân trên các thiết bị Android/iOS kể cả khi di chuyển ngầm.
- Tính toán chỉ số sinh học: Tự động tính toán Calo tiêu thụ (kcal) và Quãng đường di chuyển (km) dựa trên cân nặng và chiều cao.
- Lưu trữ Offline: Lưu trữ dữ liệu ngầm bằng AsyncStorage và tự động reset số bước khi sang ngày mới (00:00).
- Đồng bộ 1 chạm: Nút Đồng bộ ngay truyền dữ liệu đếm bước lên Backend và cập nhật thẳng vào Card "Đã tiêu hao" trên Web Dashboard.

### 2. Phân tích Món ăn AI Gemini Flash (AI Food Scanner)
- Chụp ảnh / Chọn từ Thư viện: Tích hợp expo-image-picker chụp ảnh trực tiếp bằng Camera hoặc chọn ảnh sẵn có trong Album.
- Phân tích Multimodal Vision: Gửi ảnh đĩa thức ăn tới Gemini Flash 2.0 AI để tự động nhận diện tên món ăn, tính tổng Calo và phân tích 3 chỉ số Macros: Protein (Đạm), Carbs (Đường), Fat (Béo).
- Thanh điều chỉnh Khẩu phần (Portion Multiplier): Chọn các mức 0.5x, 1.0x, 1.5x, 2.0x - chỉ số Calo & Macros tự động tính toán lại theo tỷ lệ.
- Lưu Nhật ký Bữa ăn: Ghi nhận bữa ăn vào CSDL PostgreSQL và cộng dồn tự động vào Card "Đã nạp" trên Web & Mobile.

### 3. Thanh Điều Hướng Bottom Navigation Bar (4 Tabs)
Thanh Tab Bar hiện đại ở đáy ứng dụng với giao diện sắc nét, icon hoạt họa mượt từ lucide-react-native:
- Tổng quan (HomeScreen): Đếm bước chân, calo tiêu hao, quãng đường, đồng bộ dữ liệu.
- Quét AI (FoodScanScreen): Chụp ảnh món ăn & phân tích dinh dưỡng AI.
- Lộ trình (PlanScreen): Theo dõi Kế hoạch Dinh dưỡng cá nhân hóa, mục tiêu Calo 2,000 kcal và phân bổ 4 bữa ăn.
- Cá nhân (ProfileScreen): Quản lý Thông tin tài khoản, Kiểm tra địa chỉ máy chủ API và Đăng xuất an toàn.

### 4. Bảo Mật & Xác Thực JWT Token
- Lưu trữ JWT Token an toàn trong AsyncStorage.
- Tự động kiểm tra token và chuyển thẳng vào ứng dụng mà không cần đăng nhập lại.

---

## Hướng Dẫn Cài Đặt & Chạy Ứng Dụng (Installation Guide)

### 1. Yêu cầu môi trường (Prerequisites)
- Node.js: Phiên bản >= 18.x
- Ứng dụng Expo Go: Tải sẵn trên điện thoại Android (Google Play Store) hoặc iOS (App Store).
- Backend & CSDL: Đã khởi động Backend Python (uvicorn app.main:app --host 0.0.0.0 --port 8000) và Docker PostgreSQL.

---

### 2. Các bước cài đặt & Khởi động

#### Bước 1: Chuyển vào thư mục mobile
```powershell
cd mobile
```

#### Bước 2: Cài đặt các gói phụ thuộc (Dependencies)
```powershell
npm install
```

#### Bước 3: Khởi động Expo Dev Server ở chế độ LAN
```powershell
npx expo start --clear --lan
```
*(Hoặc dùng npx expo start --clear --tunnel nếu bạn muốn chạy qua đường truyền đám mây Tunnel)*.

#### Bước 4: Trải nghiệm trên điện thoại
- Mở ứng dụng Expo Go trên điện thoại.
- Đưa camera quét mã QR hiển thị trong cửa sổ Terminal.
- Ứng dụng sẽ nạp giao diện và sẵn sàng sử dụng!

---

## Cấu Trúc Thư Mục (Directory Structure)

```text
mobile/
├── assets/                  # Hình ảnh icon, splash screen
├── components/              # Các UI Component chung (LogoMark...)
├── navigation/
│   └── MainTabNavigator.jsx # Thanh điều hướng Bottom Navigation 4 Tab
├── screens/
│   ├── LoginScreen.jsx      # Màn hình Đăng nhập JWT Token
│   ├── HomeScreen.jsx       # Tab 1: Đếm bước chân & Calo tiêu hao
│   ├── FoodScanScreen.jsx   # Tab 2: Chụp ảnh & Phân tích Gemini AI
│   ├── PlanScreen.jsx       # Tab 3: Kế hoạch Dinh dưỡng
│   └── ProfileScreen.jsx    # Tab 4: Thông tin cá nhân & Đăng xuất
├── theme.js                 # Token màu sắc & Style chuẩn giao diện
├── App.js                   # Màn hình điều hướng gốc (Root Navigator)
├── app.json                 # Cấu hình Expo, Camera & Permissions
├── babel.config.js          # Cấu hình Babel preset cho Expo SDK 54
├── metro.config.js          # Đăng ký extension .jsx cho Metro
└── package.json             # Danh sách thư viện phụ thuộc npm
```

---

## Lưu Ý Khi Chạy Ứng Dụng
- Đảm bảo máy tính và điện thoại kết nối cùng một mạng Wi-Fi khi chạy chế độ --lan.
- Nếu địa chỉ IP Wi-Fi của máy tính bị thay đổi, bạn chỉ cần cập nhật hằng số BACKEND_IP trong App.js hoặc nhập IP trên màn hình Đăng nhập.
