INSERT INTO medical_conditions(code, name) VALUES
  ('E11','Đái tháo đường típ 2'),
  ('I10','Tăng huyết áp'),
  ('E78','Rối loạn lipid máu');

INSERT INTO allergens(name) VALUES
  ('Đậu phộng'), ('Hải sản có vỏ'), ('Sữa bò'), ('Gluten');

INSERT INTO doc_categories(name, slug) VALUES
  ('Hướng dẫn dinh dưỡng','huong-dan-dinh-duong'),
  ('Nghiên cứu y khoa','nghien-cuu-y-khoa');

INSERT INTO exercises(name, met_value, category) VALUES
  ('Đi bộ', 3.5, 'Cardio'),
  ('Chạy bộ', 8.0, 'Cardio'),
  ('Tập tạ', 5.0, 'Strength');

INSERT INTO foods(name, serving_desc, serving_gram, calories_kcal, protein_g, carb_g, fat_g, source) VALUES
  ('Phở bò','1 tô',400,430,25,55,12,'Tự nhập'),
  ('Cơm tấm sườn','1 dĩa',450,620,28,70,22,'Tự nhập'),
  ('Salad ức gà','1 dĩa',300,280,32,12,10,'USDA');

INSERT INTO drug_categories(id, name) VALUES
  (1, 'Thuốc giảm cân'), (2, 'Thuốc cảm sốt');

INSERT INTO drugs(id, category_id, name, active_ingredient, indications, side_effects, contraindications, status, status_note) VALUES
  ('a0000000-0000-0000-0000-000000000001', 1, 'Sibutramine', 'Sibutramine', 'Hỗ trợ giảm cân', 'Tăng huyết áp, nguy cơ đột quỵ, tim mạch', 'Bệnh tim mạch, tăng huyết áp chưa kiểm soát', 'BANNED', 'Bị cấm lưu hành tại Việt Nam do nguy cơ tim mạch và đột quỵ nghiêm trọng.'),
  ('a0000000-0000-0000-0000-000000000002', 1, 'Reductil', 'Sibutramine', 'Giảm cân', 'Tăng nguy cơ biến cố tim mạch', 'Tiền sử bệnh mạch vành, đột quỵ', 'BANNED', 'Bị rút giấy phép lưu hành tại Việt Nam do chứa Sibutramine.'),
  ('a0000000-0000-0000-0000-000000000003', 1, 'Phentermine', 'Phentermine', 'Giảm thèm ăn', 'Tăng nhịp tim, mất ngủ, nghiện', 'Bệnh tim, tăng áp phổi', 'BANNED', 'Cấm sử dụng trong thực phẩm chức năng và thuốc giảm cân không kê đơn tại Việt Nam.'),
  ('a0000000-0000-0000-0000-000000000004', 2, 'Pseudoephedrine', 'Pseudoephedrine', 'Giảm sung huyết mũi', 'Tăng huyết áp, hồi hộp', 'Bệnh tăng huyết áp nặng', 'RESTRICTED', 'Thuốc kê đơn, cần quản lý đặc biệt và có chỉ định của bác sĩ tại Việt Nam.'),
  ('a0000000-0000-0000-0000-000000000005', 2, 'Paracetamol', 'Paracetamol', 'Giảm đau hạ sốt', 'Hại gan khi dùng quá liều', 'Suy gan nặng', 'ALLOWED', 'Được phép sử dụng theo đúng liều lượng khuyến cáo.');