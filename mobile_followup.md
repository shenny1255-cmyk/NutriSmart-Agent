# Kế hoạch cải thiện App NutriSmart

## 1. Hiện trạng

App mobile hiện có các màn:

- Đăng nhập.
- Trang chủ và theo dõi bước chân.
- Phân tích ảnh món ăn.
- Xem lộ trình.
- Xem hồ sơ và đăng xuất.

Backend đã kiểm tra tên người dùng, tên món ăn và tên danh mục; emoji hoặc ký tự đặc biệt không hợp lệ sẽ bị từ chối. Màn phân tích ảnh mobile cũng đã xử lý ảnh không phải món ăn: không hiển thị kcal và không cho lưu vào nhật ký.

Các vấn đề chính còn lại là cấu hình API bị lặp, IP máy chủ viết cứng, token lưu chưa an toàn và một số tính năng chưa đồng bộ với web.

## 2. Mức ưu tiên 1 — Hạ tầng API và bảo mật

### 2.1. Tạo API client dùng chung

Tạo `mobile/services/api.js` để:

- Quản lý một `baseURL` duy nhất.
- Tự đọc và gắn access token vào request.
- Chuẩn hóa timeout.
- Chuẩn hóa thông báo lỗi tiếng Việt.
- Khi nhận HTTP 401, xóa phiên đăng nhập và yêu cầu đăng nhập lại.
- Hỗ trợ cả JSON và upload ảnh bằng `FormData`.

Các màn không được tự ghép URL hoặc tự xử lý token riêng nữa.

### 2.2. Bỏ IP viết cứng

Hiện App đang phụ thuộc vào `10.120.56.85`. Cần thay bằng cấu hình theo môi trường:

- Development: đọc từ biến môi trường Expo.
- Production: dùng URL HTTPS chính thức.
- Có thể có màn cấu hình máy chủ riêng cho bản demo nội bộ.
- Không sửa IP rải rác trong từng màn hình.

### 2.3. Lưu token bằng SecureStore

- Cài và dùng `expo-secure-store`.
- Chuyển access token từ `AsyncStorage` sang SecureStore.
- `AsyncStorage` chỉ giữ dữ liệu không nhạy cảm như tùy chọn giao diện hoặc cache.
- Khi đăng xuất hoặc token hết hạn, xóa token an toàn.

### 2.4. Sử dụng HTTPS khi phát hành

- Không truyền JWT và dữ liệu sức khỏe qua HTTP trong production.
- Chỉ cho phép HTTP ở môi trường development nội bộ.
- Không hiển thị lỗi kỹ thuật hoặc URL nội bộ cho người dùng cuối.

## 3. Mức ưu tiên 2 — Hoàn thiện phân tích món ăn

Luồng đề xuất:

1. Người dùng chụp hoặc chọn ảnh.
2. App hiển thị ảnh và trạng thái đang phân tích.
3. Nếu ảnh không phải món ăn hoặc không đủ rõ:
   - Hiển thị lý do dễ hiểu.
   - Không hiển thị kcal.
   - Không cho lưu nhật ký.
   - Cho chọn hoặc chụp ảnh khác.
4. Nếu ảnh hợp lệ:
   - Hiển thị tên món, kcal, protein, carb, fat và độ tin cậy.
   - Cho chọn khẩu phần.
   - Cho chọn loại bữa: sáng, trưa, tối hoặc ăn nhẹ.
5. Khi lưu:
   - Khóa nút để chống gửi trùng.
   - Hiển thị xác nhận đã lưu.
   - Cập nhật tổng kcal trang chủ khi quay lại.

Cần bổ sung:

- Giữ ảnh và kết quả khi chuyển tab rồi quay lại.
- Nút “Chọn ảnh khác” rõ ràng nhưng không bị lặp.
- Phân biệt lỗi mất mạng, hết phiên và dịch vụ AI tạm thời lỗi.
- Không bao giờ dùng kết quả dinh dưỡng giả khi AI thất bại.

## 4. Mức ưu tiên 3 — UX dùng chung

### Trạng thái tải

- Dùng skeleton cho trang chủ, lộ trình và hồ sơ.
- Không để màn hình trắng trong lúc chờ API.
- Không giữ dữ liệu cũ mà không báo đang tải lại.

### Mất mạng và thử lại

- Có trạng thái offline hoặc không kết nối được máy chủ.
- Mỗi màn tải dữ liệu cần có nút “Thử lại”.
- Giữ dữ liệu gần nhất nếu phù hợp và ghi rõ đó là dữ liệu đã lưu trước đó.

### Thông báo lỗi

- Dùng câu tiếng Việt ngắn, hướng dẫn được hành động tiếp theo.
- Không hiển thị `Network Error`, stack trace hoặc lỗi database.
- Thông báo hết phiên phải đưa người dùng về đăng nhập.

### Đăng nhập

- Thêm nút hiện/ẩn mật khẩu.
- Kiểm tra định dạng email trước khi gọi API.
- Khóa nút đăng nhập khi đang gửi.
- Có thông báo riêng cho sai mật khẩu, mất mạng và máy chủ không phản hồi.

## 5. Mức ưu tiên 4 — Đồng bộ tính năng với web

Triển khai lần lượt:

1. Nhật ký bữa ăn, vận động và cân nặng.
2. Check-in tiến độ 14 ngày.
3. Cập nhật hồ sơ sức khỏe.
4. Thông báo và nhắc check-in.
5. Trợ lý AI nếu trải nghiệm mobile thực sự cần.

Không nên đưa toàn bộ trang quản trị lên mobile. Admin và chuyên gia có thể tiếp tục dùng web cho các bảng dữ liệu lớn.

## 6. Tiêu chí hoàn thành

- Không còn IP backend lặp trong các màn hình.
- Mọi request đi qua API client dùng chung.
- JWT được lưu bằng SecureStore.
- HTTP 401 luôn kết thúc phiên đúng cách.
- Không lưu trùng bữa ăn khi bấm nhiều lần.
- Ảnh không phải món ăn không thể tạo nhật ký hoặc kcal.
- Chuyển tab không làm mất kết quả phân tích đang xem.
- Mỗi màn có đầy đủ loading, empty, error và retry state.
- Android bundle export thành công với Expo SDK 54.
- Kiểm tra thủ công trên Expo Go hoặc thiết bị Android thật.

## 7. Thứ tự triển khai đề xuất cho buổi tiếp theo

1. Tạo cấu hình môi trường và API client.
2. Chuyển token sang SecureStore.
3. Refactor Login, Home, Profile, Plan và FoodScan dùng API client.
4. Hoàn thiện luồng FoodScan và loại bữa ăn.
5. Thêm loading, retry và offline UX dùng chung.
6. Export Android bundle và kiểm thử trên thiết bị thật.

## 8. Checklist kiểm thử nhanh

- Đăng nhập đúng và sai mật khẩu.
- Mất mạng khi đăng nhập.
- Token hết hạn khi đang ở mỗi tab.
- Chọn ảnh món ăn hợp lệ.
- Chọn ảnh không phải món ăn.
- Gemini không phản hồi.
- Bấm nút lưu nhiều lần liên tiếp.
- Chuyển tab trong lúc đang phân tích.
- Đóng và mở lại App sau khi đăng nhập.
- Đăng xuất và xác nhận token đã bị xóa.
