# Dữ liệu dinh dưỡng (GĐ1)

| File | Nội dung | Dùng ở đâu |
|---|---|---|
| `food_composition_vn2007.csv` | 526 thực phẩm của **Bảng thành phần thực phẩm Việt Nam** (Viện Dinh dưỡng, NXB Y học 2007), giá trị cho 100 g phần ăn được | Bảng `food_composition`, API `GET /api/v1/catalog/food-composition`, Vision bóc tách thành phần (GĐ3) |
| `dish_ingredients.json` | 76 món phổ biến → nguyên liệu theo công thức thường gặp | Warning Engine (`services/guardrails.py`) bắt dị ứng ẩn trong tên món |

## Nguồn và cách tạo bảng thành phần

- Nguồn: bản PDF chính thức do FAO lưu trữ: https://www.fao.org/fileadmin/templates/food_composition/documents/pdf/VTN_FCT_2007.pdf
- CSV được **trích tự động** bằng `scripts/import_vn_fct.py`, không gõ tay, không để AI đoán số. Cột `book_page` và `code` là trang và mã số trong sách để đối chiếu từng dòng.
- Tạo lại: tải PDF rồi chạy `PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/import_vn_fct.py <file.pdf>`.
- Ô trống = sách không có số liệu (hoặc số mơ hồ, xem dưới). Code giữ nguyên là thiếu, không thay bằng 0.

### Cột `check_note`: các dòng cần nhóm xem lại (90 dòng)

| Loại ghi chú | Số dòng | Ý nghĩa | Cách duyệt |
|---|---|---|---|
| `số mơ hồ, tra trang gốc: sodium '31'` | 87 | Trong PDF, số 1 chữ số dính liền mã nguồn ("01" = 0, nguồn 1). Token "31" không có cột nguồn riêng nên không biết là 3 mg hay 31 mg → script để trống | Mở trang `book_page`, điền số đúng vào cột `sodium_mg` |
| `Atwater lệch` | 2 | 4·P + 9·L + 4·G khác năng lượng ghi trong sách >15% | Rượu trắng lệch là bình thường (năng lượng từ cồn). Riềng: đối chiếu sách |
| Ghi chú tay trong `KNOWN_ISSUES` | 1 | Sữa bò tươi: natri 380 mg/100 g, trong khi USDA ghi 43 mg | Đối chiếu sách in; nếu in nhầm thì ghi rõ trong khóa luận |

### Quy trình duyệt

1. Mở CSV (Excel: Data → From Text/CSV, chọn UTF-8).
2. Ưu tiên ~200 thực phẩm phổ biến nhất (gạo, thịt, cá, trứng, rau, quả, gia vị) và các dòng có `check_note`.
3. Đối chiếu với trang `book_page`; đúng thì đổi `review_status` thành `DA_DUYET`, sai thì sửa số và đổi thành `CAN_SUA` kèm ghi chú.
4. Gửi PR. Sau khi merge, chạy `scripts/load_food_composition.py` để nạp lại vào DB (DB mới thì backend tự nạp khi bảng rỗng).

Lưu ý: chạy lại `import_vn_fct.py` sẽ ghi đè CSV, mất các chỉnh sửa và trạng thái duyệt. Sau khi nhóm bắt đầu duyệt thì chỉ sửa CSV trực tiếp.

## Bảng món → nguyên liệu

- Nguyên liệu ghi theo **công thức phổ biến**, chưa có chuyên gia duyệt (`review_status: CHUA_DUYET`).
- Chỉ ghi thứ có ý nghĩa với dị ứng/bệnh nền. Gia vị lượng nhỏ (đường, muối nêm) **không** ghi để tránh báo động giả; dùng cờ lượng `nhiều đường`, `nhiều muối`, `chiên ngập dầu` cho món thật sự nhiều.
- Tên dài khớp trước: "Bún bò Nam Bộ" không bị hiểu thành "bún bò" (alias của Bún bò Huế).
- Thêm món: thêm một mục vào `dishes`, chạy `pytest tests/test_dish_ingredients.py` (kiểm tra trùng tên, chữ dễ gây báo động giả) và `scripts/guardrail_eval.py`.
