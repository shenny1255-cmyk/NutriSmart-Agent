-- Danh mục món ăn + bài tập cho màn Nhật ký (nhập tay).
-- Seed gốc (11_seed.sql) chỉ có 3 món / 3 bài tập, không đủ để dùng thật.
--
-- Dùng WHERE NOT EXISTS thay vì ON CONFLICT: bảng foods KHÔNG unique theo tên
-- (vision/log-meal sinh một dòng foods cho mỗi lần phân tích ảnh nên tên có thể
-- đã trùng sẵn) → chạy lại file này nhiều lần vẫn an toàn, không cần index unique.

INSERT INTO foods(name, serving_desc, serving_gram, calories_kcal, protein_g, carb_g, fat_g, source)
SELECT v.name, v.serving_desc, v.serving_gram, v.calories_kcal, v.protein_g, v.carb_g, v.fat_g, v.source
FROM (VALUES
  ('Bún bò Huế',          '1 tô',   450, 480, 26, 52, 18, 'Tự nhập'),
  ('Bún chả',             '1 suất', 400, 520, 28, 55, 20, 'Tự nhập'),
  ('Bánh mì thịt',        '1 ổ',    200, 460, 20, 50, 19, 'Tự nhập'),
  ('Bánh cuốn',           '1 dĩa',  300, 350, 14, 55,  8, 'Tự nhập'),
  ('Xôi gà',              '1 hộp',  350, 600, 24, 78, 20, 'Tự nhập'),
  ('Hủ tiếu',             '1 tô',   400, 420, 22, 56, 12, 'Tự nhập'),
  ('Mì Quảng',            '1 tô',   400, 500, 25, 60, 17, 'Tự nhập'),
  ('Cháo gà',             '1 tô',   350, 280, 18, 38,  6, 'Tự nhập'),
  ('Cơm gà xối mỡ',       '1 dĩa',  450, 680, 32, 72, 28, 'Tự nhập'),
  ('Cơm rang dưa bò',     '1 dĩa',  400, 640, 26, 76, 24, 'Tự nhập'),
  ('Cơm trắng',           '1 chén', 150, 200,  4, 44,  0, 'USDA'),
  ('Thịt kho trứng',      '1 phần', 150, 320, 22,  6, 22, 'Tự nhập'),
  ('Cá kho tộ',           '1 phần', 150, 260, 25,  8, 14, 'Tự nhập'),
  ('Canh chua cá',        '1 tô',   300, 150, 14, 12,  5, 'Tự nhập'),
  ('Rau muống luộc',      '1 dĩa',  200,  45,  4,  7,  1, 'USDA'),
  ('Đậu hũ sốt cà',       '1 phần', 200, 210, 14, 12, 12, 'Tự nhập'),
  ('Trứng luộc',          '1 quả',   55,  78,  6,  1,  5, 'USDA'),
  ('Ức gà luộc',          '100g',   100, 165, 31,  0,  4, 'USDA'),
  ('Sữa chua không đường','1 hộp',  100,  60,  4,  7,  2, 'USDA'),
  ('Sữa tươi không đường','1 ly',   240, 120,  8, 12,  5, 'USDA'),
  ('Chuối',               '1 quả',  120, 105,  1, 27,  0, 'USDA'),
  ('Táo',                 '1 quả',  180,  95,  1, 25,  0, 'USDA'),
  ('Yến mạch',            '1 chén',  80, 300, 11, 54,  6, 'USDA'),
  ('Bánh mì đen',         '1 lát',   40, 100,  4, 18,  1, 'USDA'),
  ('Trà sữa trân châu',   '1 ly',   500, 450,  5, 80, 12, 'Tự nhập'),
  ('Cà phê sữa đá',       '1 ly',   250, 180,  3, 28,  6, 'Tự nhập')
) AS v(name, serving_desc, serving_gram, calories_kcal, protein_g, carb_g, fat_g, source)
WHERE NOT EXISTS (SELECT 1 FROM foods f WHERE f.name = v.name);

INSERT INTO exercises(name, met_value, category)
SELECT v.name, v.met_value, v.category
FROM (VALUES
  ('Đi bộ nhanh',   4.3, 'Cardio'),
  ('Chạy bền',      9.8, 'Cardio'),
  ('Đạp xe',        7.5, 'Cardio'),
  ('Bơi lội',       8.3, 'Cardio'),
  ('Nhảy dây',     11.0, 'Cardio'),
  ('HIIT',          9.0, 'Cardio'),
  ('Yoga',          3.0, 'Flexibility'),
  ('Gym toàn thân', 6.0, 'Strength'),
  ('Chống đẩy',     8.0, 'Strength'),
  ('Cầu lông',      5.5, 'Sport'),
  ('Bóng đá',       7.0, 'Sport'),
  ('Leo cầu thang', 8.8, 'Cardio')
) AS v(name, met_value, category)
WHERE NOT EXISTS (SELECT 1 FROM exercises e WHERE e.name = v.name);
