# NutriSmart Mobile

Ứng dụng Expo SDK 54 dành cho người dùng NutriSmart: theo dõi bước chân, nhật ký bữa ăn,
vận động và cân nặng, phân tích ảnh món ăn, lộ trình cá nhân hóa, check-in 14 ngày,
thông báo và trợ lý dinh dưỡng AI.

## Chuẩn bị môi trường

- Node.js từ `20.19.x`.
- Backend NutriSmart và PostgreSQL đang chạy.
- Expo Go hoặc thiết bị Android/iOS thật.
- Máy tính và điện thoại dùng cùng mạng khi kết nối backend nội bộ.

```powershell
cd mobile
npm install
Copy-Item .env.example .env.local
```

Sửa `.env.local` để điện thoại truy cập được backend:

```dotenv
EXPO_PUBLIC_API_URL=http://192.168.1.10:8000/api/v1
```

Không commit `.env.local`. Bản phát hành bắt buộc dùng URL HTTPS. Nếu không có biến môi
trường trong development, ứng dụng thử suy ra địa chỉ máy chạy Expo nhưng `.env.local`
vẫn là cách cấu hình ổn định nhất.

## Chạy ứng dụng

```powershell
npx expo start --clear --lan
```

## Kiểm tra trước khi bàn giao

```powershell
npm run check
npm run test:architecture
npm run export:android
```

Sau khi export thành công, vẫn phải kiểm tra thủ công trên Expo Go hoặc thiết bị Android
thật: đăng nhập, hết phiên, offline, cảm biến, phân tích ảnh hợp lệ/không hợp lệ, chuyển
tab, chống lưu trùng bữa ăn, nhật ký, check-in, sửa hồ sơ, thông báo và trợ lý AI.

## Kiến trúc chính

```text
mobile/
├── components/             # Thành phần UI và trạng thái dùng chung
├── config/env.js           # Cấu hình EXPO_PUBLIC_API_URL
├── context/AuthContext.jsx # Trạng thái phiên đăng nhập toàn cục
├── navigation/             # Bottom tabs
├── screens/                # Các màn đăng nhập, theo dõi, lộ trình, check-in, hồ sơ và AI
├── services/api.js         # API client, timeout, lỗi và HTTP 401
├── services/session.js     # SecureStore cho JWT
└── scripts/                # Kiểm tra kiến trúc tự động
```

JWT được lưu bằng SecureStore trên Android/iOS. AsyncStorage chỉ lưu cache bước chân.
Bản web xem trước dùng `sessionStorage` vì SecureStore không hỗ trợ web.

## Giới hạn cảm biến

`Pedometer.watchStepCount` của Expo không phát cập nhật khi ứng dụng ở background. Mobile
hiện theo dõi bước chân khi ứng dụng đang mở và lưu số gần nhất vào cache. Nếu cần đồng
bộ bước chân nền chính xác trên Android, cần tích hợp Health Connect trong một hạng mục riêng.
