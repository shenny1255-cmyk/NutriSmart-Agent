# Thiết kế kho bài viết đã phê duyệt

## Trạng thái

Đã duyệt thiết kế trong hội thoại ngày 24/08/2026. Đã triển khai trong `feat/approved-article-library`.

## Mục tiêu

Tạo một kho bài viết trực quan cho người dùng NutriSmart từ dữ liệu `documents` hiện có. Kho chỉ hiển thị tài liệu đã được chuyên gia hoặc quản trị viên phê duyệt, cung cấp đoạn giới thiệu ngắn và dẫn người dùng tới bài viết gốc.

Tính năng phải giữ nguyên ranh giới nghiệp vụ hiện tại: chuyên gia tiếp tục thu thập và duyệt tài liệu trong `/expert`, còn người dùng chỉ đọc dữ liệu đã được công bố qua một API riêng.

## Quyết định đã chốt

1. Tái sử dụng bảng `documents`; không tạo bảng bài viết hoặc CMS mới.
2. Chỉ hiển thị bản ghi có `status = 'APPROVED'` và `deleted_at IS NULL`.
3. Không hiển thị toàn bộ `raw_text` trong giao diện người dùng.
4. Đoạn giới thiệu được tạo từ phần đầu `raw_text`, không gọi Ollama và không lưu thêm dữ liệu.
5. Nút **“Đọc bài gốc”** mở `source_url` trong tab mới.
6. Kho bài viết dành cho tài khoản đã đăng nhập thuộc mọi vai trò `USER`, `EXPERT`, `ADMIN`.
7. MVP có tìm kiếm, lọc danh mục và phân trang; không có bookmark, lượt xem, tags, ảnh đại diện hoặc AI summary.

## Hiện trạng liên quan

- `backend/app/models.py:304-331` đã có `DocCategory`, `Document` và enum `DRAFT | PENDING | APPROVED | REJECTED`.
- `backend/app/routers/expert.py:26-90` đã có luồng xem trước và duyệt tài liệu cho `EXPERT`/`ADMIN`.
- `backend/app/services/retrieval.py:43-68` đã coi `APPROVED` và chưa soft-delete là điều kiện nguồn RAG hợp lệ.
- `backend/app/schemas.py:565-575` có `DocumentOut`, nhưng schema này chứa `raw_text` nên không phù hợp cho API người dùng.
- `frontend/src/App.jsx:23-34,224-237` có navigation và route shell theo vai trò, nhưng chưa có route kho bài viết.
- `frontend/src/pages/AdminAudit.jsx:65-179` cung cấp pattern tìm kiếm, lọc và phân trang server-side.
- `frontend/src/pages/ExpertReview.jsx:402-484` cung cấp pattern card, metadata, loading và empty state cho tài liệu.

## Kiến trúc

### Ranh giới module

Tạo router chỉ-đọc `backend/app/routers/articles.py` dưới prefix `/api/v1/articles`. Router này chịu trách nhiệm:

- xác thực người dùng;
- lọc tài liệu được phép công bố;
- tìm kiếm, lọc danh mục, sắp xếp và phân trang;
- chuyển `raw_text` thành `excerpt` an toàn cho response;
- không thực hiện upload, sửa, duyệt hoặc xóa tài liệu.

Các mutation vẫn nằm trong `backend/app/routers/expert.py`. Không mở rộng `/expert/documents/pending` và không cho `USER` truy cập router chuyên gia.

### Luồng dữ liệu

```text
Articles.jsx
  -> GET /api/v1/articles?q=&category_id=&page=&page_size=
  -> xác thực JWT
  -> truy vấn documents APPROVED, chưa soft-delete
  -> tạo excerpt từ raw_text
  -> trả danh sách card có phân trang

Articles.jsx
  -> GET /api/v1/articles/categories
  -> chỉ lấy danh mục có ít nhất một tài liệu hợp lệ
  -> dựng bộ lọc danh mục

Người dùng bấm “Đọc bài gốc”
  -> mở source_url trong tab mới
```

## Hợp đồng API

### `GET /api/v1/articles`

Yêu cầu Bearer token hợp lệ. Mọi vai trò đã đăng nhập đều được phép gọi.

Query parameters:

| Tham số | Kiểu | Mặc định | Ràng buộc | Ý nghĩa |
|---|---:|---:|---:|---|
| `q` | string hoặc null | null | tối đa 100 ký tự | Tìm không phân biệt hoa thường trong `title` và `source_name` |
| `category_id` | integer hoặc null | null | lớn hơn 0 | Lọc chính xác theo danh mục |
| `page` | integer | 1 | từ 1 | Trang hiện tại |
| `page_size` | integer | 12 | từ 6 đến 48 | Số card mỗi trang |

Điều kiện truy vấn bắt buộc:

```python
Document.status == "APPROVED"
Document.deleted_at.is_(None)
```

Thứ tự ổn định:

1. `approved_at DESC NULLS LAST`;
2. `created_at DESC`;
3. `id DESC`.

Response `200 OK`:

```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Ăn rau xanh đúng cách",
      "excerpt": "Rau xanh cung cấp chất xơ và nhiều vi chất cần thiết…",
      "source_name": "Sức khỏe & Đời sống",
      "source_url": "https://example.com/bai-viet",
      "category": {
        "id": 3,
        "name": "Dinh dưỡng",
        "slug": "dinh-duong"
      },
      "approved_at": "2026-08-24T09:00:00+07:00"
    }
  ],
  "total": 24,
  "page": 1,
  "page_size": 12
}
```

Response không được chứa `raw_text`, `file_path`, `uploaded_by`, `approved_by` hoặc thông tin vector/chunk.

### `GET /api/v1/articles/categories`

Yêu cầu Bearer token hợp lệ. Chỉ trả danh mục có ít nhất một `Document` thỏa điều kiện công bố.

Response `200 OK`:

```json
[
  {
    "id": 3,
    "name": "Dinh dưỡng",
    "slug": "dinh-duong",
    "article_count": 12
  }
]
```

`article_count` chỉ đếm tài liệu Approved và chưa soft-delete, khác với thống kê quản trị hiện tại vốn đếm mọi tài liệu.

## Quy tắc tạo đoạn giới thiệu

Hàm thuần ở tầng router hoặc service nhỏ nhận `raw_text` và trả `excerpt`:

1. thay chuỗi khoảng trắng liên tiếp bằng một dấu cách;
2. trim hai đầu;
3. nếu nội dung không quá 220 ký tự thì trả nguyên văn;
4. nếu dài hơn, cắt tại ranh giới từ gần nhất không vượt quá 220 ký tự rồi thêm ký tự `…`;
5. nếu `raw_text` rỗng thì trả chuỗi rỗng, không làm hỏng toàn bộ response.

Việc tạo excerpt diễn ra khi serialize response. MVP không thêm cột `summary` và không chạy tác vụ nền.

## Thiết kế frontend

### Route và navigation

- Tạo `frontend/src/pages/Articles.jsx`.
- Đăng ký route `/articles` bên trong `RequireAuth` và `Shell`.
- Thêm mục **“Kho bài viết”** vào `baseNav` cho `USER`, `EXPERT`, `ADMIN`.
- Dùng icon từ sprite hiện có trong `frontend/public/icons.svg`; không thêm thư viện icon.

### API client

Mở rộng `frontend/src/lib/api.js` bằng các method dùng chung `request()`:

```javascript
articles: (params) => request(`/articles?${query}`)
articleCategories: () => request('/articles/categories')
```

Query string chỉ chứa tham số có giá trị. Không gọi `fetch` trực tiếp trong page.

### Bố cục trang

Trang dùng các token và primitive hiện có trong `frontend/src/components/ui.jsx`:

- header gồm tiêu đề **“Kho bài viết dinh dưỡng”** và mô tả ngắn;
- hàng công cụ gồm ô tìm kiếm, select danh mục và nút xóa bộ lọc;
- dòng kết quả thể hiện tổng số bài phù hợp;
- lưới card responsive: 1 cột trên mobile, 2 cột trên tablet, 3 cột trên desktop;
- phân trang **“Trang trước”** và **“Trang sau”** theo pattern của `AdminAudit.jsx`.

Mỗi card hiển thị:

- badge danh mục nếu có;
- tiêu đề;
- đoạn giới thiệu tối đa 220 ký tự;
- tên nguồn và ngày duyệt;
- nút **“Đọc bài gốc”**.

Nếu `source_url` rỗng, card vẫn xuất hiện để phản ánh đúng kho Approved nhưng thay nút bằng trạng thái **“Chưa có liên kết nguồn”** và không tạo link.

Link ngoài phải dùng `target="_blank"` và `rel="noopener noreferrer"`.

### Trạng thái giao diện

- Lần tải đầu: hiển thị skeleton card để giữ bố cục ổn định.
- Đổi tìm kiếm, danh mục hoặc trang: khóa các control cần thiết và hiển thị trạng thái đang tải.
- Lỗi API: dùng `Alert` với thông báo tiếng Việt và nút thử lại.
- Không có kết quả: hiển thị empty state và nút xóa bộ lọc nếu đang lọc.
- Search chỉ gửi khi người dùng nhấn Enter hoặc bấm nút tìm, không gọi API ở mỗi phím gõ.
- Thay đổi từ khóa hoặc danh mục luôn đặt `page` về 1.

## Bảo mật và riêng tư

- Cả hai endpoint sử dụng `get_current_user`; không phải API công khai không cần đăng nhập.
- Backend là nguồn kiểm soát cuối cùng cho trạng thái Approved; frontend không gửi hoặc chọn `status`.
- Không tái sử dụng `DocumentOut` vì schema đó làm lộ `raw_text`.
- Không trả đường dẫn file nội bộ hoặc định danh người upload/người duyệt.
- URL ngoài được mở an toàn bằng `noopener noreferrer`.
- Tính năng chỉ đọc, không thay đổi permission duyệt tài liệu của `EXPERT`/`ADMIN`.

## Hiệu năng và cơ sở dữ liệu

- MVP không cần migration mới; `idx_documents_status` hiện có hỗ trợ điều kiện trạng thái.
- Dùng pagination phía server với `count`, `offset`, `limit`; không tải toàn bộ documents về frontend.
- Search MVP chỉ áp dụng cho `title` và `source_name`. Không tìm trong toàn bộ `raw_text`, tránh full scan nội dung dài.
- Chưa thêm index trigram cho tiêu đề. Chỉ bổ sung migration index sau khi có dữ liệu đo cho thấy truy vấn chậm; không tối ưu phỏng đoán.

## Xử lý lỗi và trường hợp biên

- Query sai ràng buộc trả `422` theo FastAPI.
- Token thiếu hoặc hết hạn dùng cơ chế `401` hiện có của `request()` để đưa người dùng về đăng nhập.
- `category_id` không tồn tại trả danh sách rỗng thay vì `404`, nhất quán với semantics bộ lọc.
- Tài liệu có danh mục đã mất hoặc không có danh mục vẫn được trả với `category = null`.
- `approved_at = null` không làm mất tài liệu Approved; tài liệu này được xếp sau nhóm có ngày duyệt.
- `raw_text` rỗng tạo excerpt rỗng; card vẫn hiển thị title và metadata.
- `source_url` rỗng không tạo link giả hoặc nút có hành vi lỗi.

## Kiểm thử

### Backend — TDD

Viết test thất bại trước khi triển khai cho các trường hợp:

1. USER, EXPERT và ADMIN đã đăng nhập đều lấy được danh sách.
2. Request chưa đăng nhập bị từ chối.
3. Chỉ `APPROVED` và chưa soft-delete xuất hiện.
4. Response không có `raw_text` hoặc trường nội bộ.
5. Search theo tiêu đề và tên nguồn không phân biệt hoa thường.
6. Lọc danh mục và kết hợp search hoạt động.
7. Pagination trả đúng `items`, `total`, `page`, `page_size` và thứ tự ổn định.
8. Endpoint danh mục chỉ đếm tài liệu hợp lệ.
9. Hàm excerpt xử lý whitespace, nội dung ngắn, nội dung dài và chuỗi rỗng.
10. Bản ghi thiếu `source_url`, `category` hoặc `approved_at` được serialize an toàn.

Test tích hợp cần PostgreSQL và dùng guard skip hiện có khi DB không chạy. Luôn đặt `PYTHONUTF8=1` trên Windows.

### Frontend

- `npm run build` phải thành công.
- Manual browser verification với tài khoản user:
  - mở được `/articles` từ sidebar desktop và mobile drawer;
  - tìm kiếm, lọc, xóa lọc và đổi trang hoạt động;
  - loading, lỗi và empty state hiển thị đúng;
  - layout không tràn ở mobile, tablet và desktop;
  - link nguồn mở tab mới;
  - bài thiếu link nguồn không tạo link;
  - reload route không mất quyền truy cập khi token còn hợp lệ.

## Tiêu chí hoàn thành

- Người dùng đã đăng nhập xem được kho tài liệu Approved bằng giao diện card responsive.
- Không tài liệu PENDING, REJECTED, DRAFT hoặc soft-deleted nào xuất hiện.
- Người dùng tìm kiếm, lọc danh mục và phân trang mà không tải toàn bộ dữ liệu.
- Mỗi card có excerpt ngắn và dẫn tới nguồn khi có URL.
- API không làm lộ `raw_text` hoặc metadata nội bộ.
- Backend tests liên quan vượt qua, frontend build thành công và luồng được kiểm tra trên browser.

## Ngoài phạm vi MVP

- Trang đọc toàn bộ nội dung trong NutriSmart.
- Tóm tắt bằng Ollama hoặc lưu cột summary.
- Ảnh đại diện, featured article, tags hoặc đề xuất cá nhân hóa.
- Bookmark, chia sẻ, lượt xem, đánh giá hoặc bình luận.
- CMS/tables riêng cho bài viết.
- API không cần đăng nhập hoặc tối ưu SEO.
- Migration index tìm kiếm mới khi chưa có bằng chứng hiệu năng.
