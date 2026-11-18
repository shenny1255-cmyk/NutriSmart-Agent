# Thực nghiệm định lượng khẩu phần và vòng lặp HITL

Tài liệu này chốt quy trình đo **trước khi có kết quả**, để số liệu trong Chương 4 không phụ thuộc vào việc kết quả đẹp hay xấu.

## 1. Điều kiện dữ liệu

Bộ `backend/eval/vision_dataset/` hiện tại **chưa dùng được để đo chính thức**:

| Vấn đề | Bằng chứng | Hậu quả |
|---|---|---|
| Số gram do AI sinh ra | `scripts/extract_ground_truth_candidates.py` ghi kết quả Gemini vào cột `actual_grams` | So Gemini với chính Gemini, sai số thấp giả tạo |
| Ảnh là ảnh chụp màn hình app | Cả 26 file đều có giao diện NutriSmart, in sẵn tên món và kcal | AI đọc được đáp án trên ảnh, và không thể cân lại các đĩa này |
| Món không lặp lại | `vision_eval.py check` báo 0/26 đĩa có món tương tự ở đĩa khác | Few-shot không bao giờ được kích hoạt, learning curve phẳng |

### Cách thu thập bộ ảnh mới

1. Chọn **10 đến 12 món phổ biến, mỗi món 3 đến 4 đĩa** với khẩu phần khác nhau, tổng **30 đến 40 đĩa**. Đặt tên món thống nhất trong từng nhóm.
2. Đặt đĩa rỗng lên cân, nhấn trừ bì, cho từng thành phần vào và ghi số gram sau mỗi lần thêm.
3. Chụp ảnh gốc bằng điện thoại trước khi ăn. Không chụp màn hình, không cắt ghép, không có chữ về món ăn hay calo trong ảnh.
4. Chụp thêm một ảnh màn hình cân cho mỗi thành phần và lưu riêng làm minh chứng. Ảnh minh chứng không đưa vào thư mục `images/`.
5. Ghi `ground_truth.csv` theo mẫu dưới đây.

```csv
image_file,dish_name,component_name,actual_grams,note,gt_source,weighed_by,weighed_at,plate_id,kcal_per_100g
pho_bo_01.jpg,Phở bò,Bánh phở,182,,WEIGHED,Nguyễn Văn A,2026-11-25,pho_bo_01,
pho_bo_01.jpg,Phở bò,Nước dùng,350,,WEIGHED,Nguyễn Văn A,2026-11-25,pho_bo_01,12
```

| Cột mới | Ý nghĩa |
|---|---|
| `gt_source` | Chỉ ghi `WEIGHED` khi số liệu đọc từ cân |
| `weighed_by`, `weighed_at` | Người cân và ngày cân |
| `plate_id` | Mã đĩa thật. Một đĩa chụp nhiều ảnh thì dùng chung mã để không bị rò rỉ giữa tập ví dụ và tập đo |
| `kcal_per_100g` | Để trống nếu tên có trong bảng thực phẩm VN 2007. Với món khác, ghi số kèm nguồn ở cột `note` |

## 2. Kịch bản thực nghiệm

**Câu hỏi nghiên cứu:** ca sửa đã được chuyên gia duyệt có làm giảm sai số ước lượng khẩu phần ở các đĩa mới hay không?

- **H0:** few-shot không làm thay đổi MAE kcal trên đĩa.
- **H1:** few-shot làm giảm MAE kcal trên đĩa.
- **Chỉ số chính:** MAE kcal trên tổng đĩa, ở mức kho đầy. Các chỉ số khác chỉ mang tính mô tả.

| Điều kiện | Mô tả | Vai trò |
|---|---|---|
| A. Lượt đầu | Gemini ước lượng gram, kcal tra bảng | Mốc so sánh (0 ca) |
| B. Lượt 2 không ví dụ | Gọi lại lượt tinh chỉnh với danh sách ví dụ rỗng | Đối chứng: tách tác dụng của việc nhìn lại |
| C. Few-shot N ca | Lượt tinh chỉnh với ví dụ truy hồi từ kho N ca | Điều kiện can thiệp |
| D. Cách cũ | Kcal tổng do AI tự đoán | Mốc của phiên bản trước GĐ3 |

**Thiết kế chống sai lệch**

- **Kiểm định chéo 5 fold theo `plate_id`:** đĩa đang đo không bao giờ nằm trong kho ví dụ của chính nó.
- **Kho lồng nhau:** kho 5 ca là phần đầu của kho 10 ca, nên đường cong chỉ thay đổi theo số ca.
- **So sánh theo cặp:** mọi điều kiện dùng chung một kết quả lượt đầu trên từng đĩa.
- **Lặp 3 lần** lượt tinh chỉnh để giảm dao động của mô hình, và **ghim một model** trong toàn bộ lần chạy.
- **Mức kho:** 0, 5, 10, 20 và đầy kho (khoảng 24 đến 32 ca với 30 đến 40 đĩa). Mốc 50 và 100 ca trong kế hoạch cần trên 60 và 125 đĩa, nên chưa đo được với cỡ mẫu này.

**Quy tắc kết luận (chốt trước khi chạy)**

| Kết luận | Điều kiện trên hiệu MAE theo cặp |
|---|---|
| GIẢM RÕ RỆT | KTC 95% nằm hoàn toàn dưới 0 và MAE giảm từ 10% trở lên |
| GIẢM NHƯNG DƯỚI NGƯỠNG 10% | KTC 95% nằm hoàn toàn dưới 0, MAE giảm dưới 10% |
| CHƯA ĐỦ BẰNG CHỨNG | KTC 95% chứa 0 |
| SAI SỐ TĂNG | KTC 95% nằm hoàn toàn trên 0 |

Giả thuyết HITL chỉ được coi là có dữ liệu ủng hộ khi few-shot đạt **GIẢM RÕ RỆT so với cả A và B**. Không đổi ngưỡng, prompt, seed hay loại đĩa sau khi đã xem kết quả. Nếu buộc phải đổi, phải chạy lại toàn bộ và ghi rõ trong báo cáo.

## 3. Lệnh chạy

Chạy từ thư mục `backend/`:

```bash
# Kiểm tra dữ liệu, không gọi Gemini
PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/vision_eval.py check

# Chỉ đo MAE lượt đầu
PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/vision_eval.py mae

# Đo đầy đủ learning curve
PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/vision_eval.py curve --levels 0,5,10,20
```

Với 40 đĩa, lệnh `curve` gọi Gemini tối đa khoảng 640 lượt. Phản hồi được lưu lại, nên nếu bị gián đoạn thì chạy lại đúng lệnh đó để tiếp tục. Kết quả nằm ở `backend/eval/results/`.

## 4. Bảng đề xuất cho Chương 4

Các ô `[...]` được điền từ `vision_eval_report.md`. Không điền số từ file có đuôi `_DRYRUN`.

**Bảng 4.a. Đặc điểm bộ dữ liệu đánh giá**

| Đặc điểm | Giá trị |
|---|---|
| Số đĩa đã cân / số món khác nhau | [...] / [...] |
| Số thành phần đã cân | [...] |
| Khối lượng đĩa trung bình (nhỏ nhất đến lớn nhất) | [...] g ([...] đến [...]) |
| Năng lượng đĩa trung bình (nhỏ nhất đến lớn nhất) | [...] kcal ([...] đến [...]) |
| Thiết bị cân, độ chia | [...] |
| Đĩa bị loại và lý do | [...] |

**Bảng 4.b. Cấu hình thực nghiệm**

| Tham số | Giá trị |
|---|---|
| Model / commit | [...] / [...] |
| Số fold / số lần lặp / seed | 5 / 3 / 42 |
| Truy hồi ví dụ | Trigram theo tên món, ngưỡng 0.35 (chốt trước khi đo), tối đa 3 ví dụ |
| Nguồn giá trị ví dụ | Số cân thật, mô phỏng chuyên gia duyệt |

**Bảng 4.c. Sai số của lượt nhận diện đầu** (mục 1 của báo cáo kết quả)

| Chỉ số | n | MAE | KTC 95% | WAPE | Sai lệch trung bình |
|---|---|---|---|---|---|
| Tổng khối lượng đĩa (g) | [...] | [...] | [...] | [...] | [...] |
| Tổng năng lượng đĩa (kcal) | [...] | [...] | [...] | [...] | [...] |
| Từng thành phần (g) | [...] | [...] | [...] | - | - |
| Kcal tổng do AI tự đoán, cách cũ | [...] | [...] | [...] | - | - |

**Bảng 4.d. Learning curve theo số ca trong kho** (mục 2 của báo cáo kết quả)

| Số ca trong kho | Đĩa có ví dụ khớp | MAE kcal (KTC 95%) | MAE gram (KTC 95%) | Thay đổi MAE kcal so với 0 ca |
|---|---|---|---|---|
| 0 | 0/[...] | [...] | [...] | mốc so sánh |
| 5 | [...] | [...] | [...] | [...] |
| 10 | [...] | [...] | [...] | [...] |
| 20 | [...] | [...] | [...] | [...] |
| Đầy kho ([...] ca) | [...] | [...] | [...] | [...] |
| Đối chứng: lượt 2 không ví dụ | - | [...] | [...] | [...] |

**Hình 4.e.** Learning curve MAE kcal, dùng file `vision_eval_curve_kcal.svg`.

**Bảng 4.f. Kiểm định giả thuyết chính** (mục 3 của báo cáo kết quả)

| So sánh | n | Hiệu MAE (kcal) | KTC 95% của hiệu | Thay đổi | Đĩa tốt hơn/kém hơn/bằng | p | Kết luận |
|---|---|---|---|---|---|---|---|
| Few-shot so với lượt đầu | [...] | [...] | [...] | [...] | [...] | [...] | [...] |
| Few-shot so với lượt 2 không ví dụ | [...] | [...] | [...] | [...] | [...] | [...] | [...] |

### Mẫu nhận định theo từng kết quả

- **Được ủng hộ:** "Trên [n] đĩa cân thật, few-shot làm MAE kcal giảm [x]% so với lượt đầu (KTC 95% của hiệu: [a] đến [b] kcal) và giảm [y]% so với đối chứng không có ví dụ."
- **Giảm so với lượt đầu nhưng không hơn đối chứng:** "Sai số giảm chủ yếu do lượt nhìn lại, chưa đủ bằng chứng cho thấy ví dụ của chuyên gia đóng góp thêm."
- **Chưa đủ bằng chứng:** "Với cỡ mẫu [n] đĩa, thực nghiệm chưa phát hiện được khác biệt có ý nghĩa. Kết quả này không chứng minh few-shot vô tác dụng."
- **Sai số tăng:** "Few-shot làm sai số tăng [x]%, nhiều khả năng do ví dụ của món tương tự kéo khẩu phần lệch khỏi đĩa đang xét. Nhóm chưa nên bật tính năng này mặc định."

### Hạn chế cần nêu trong khóa luận

- Giá trị ví dụ lấy từ số cân thật, nên kết quả là **mức trần** của vòng lặp HITL. Chuyên gia duyệt qua giao diện có thể kém chính xác hơn.
- Cỡ mẫu 30 đến 40 đĩa do nhóm tự chuẩn bị, chưa đại diện cho mọi món và điều kiện chụp.
- Thực nghiệm chỉ dùng nhánh tìm theo tên món, chưa đánh giá nhánh embedding `bge-m3`.
- Ngưỡng tên món 0.35 được nhóm chốt trước khi đo để khớp các biến thể của cùng một món, ví dụ "Phở bò tái" và "Phở bò chín" (0.4375). Đổi lại, ngưỡng này cũng khớp một số món khác nhau có tên gần giống, ví dụ "Phở bò" và "Phở gà" (0.40), "Cơm gà" và "Cơm bò" (0.40), nên ví dụ truy hồi có thể không đúng món.
- Kcal phụ thuộc vào bảng thực phẩm VN 2007 và bảng ánh xạ thành phần, hai nguồn này còn ở trạng thái `CHUA_DUYET`.
