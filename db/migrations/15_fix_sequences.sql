-- Đồng bộ lại sequence của các bảng được seed bằng ID tường minh.
--
-- INSERT có chỉ định id (11_seed.sql: drug_categories 1,2) KHÔNG làm sequence nhích,
-- nên bản ghi đầu tiên tạo qua giao diện quản trị sẽ xin id = 1 và vỡ vì trùng khóa
-- chính. Task 14 mở màn CRUD danh mục nên lỗi này mới lộ ra.
--
-- setval(..., false) nghĩa là "giá trị kế tiếp đúng bằng tham số" — dùng max(id)+1 để
-- an toàn cả khi bảng đang rỗng.
SELECT setval(pg_get_serial_sequence('drug_categories', 'id'),
              (SELECT COALESCE(MAX(id), 0) + 1 FROM drug_categories), false);

SELECT setval(pg_get_serial_sequence('doc_categories', 'id'),
              (SELECT COALESCE(MAX(id), 0) + 1 FROM doc_categories), false);

SELECT setval(pg_get_serial_sequence('medical_conditions', 'id'),
              (SELECT COALESCE(MAX(id), 0) + 1 FROM medical_conditions), false);

SELECT setval(pg_get_serial_sequence('allergens', 'id'),
              (SELECT COALESCE(MAX(id), 0) + 1 FROM allergens), false);

SELECT setval(pg_get_serial_sequence('exercises', 'id'),
              (SELECT COALESCE(MAX(id), 0) + 1 FROM exercises), false);
