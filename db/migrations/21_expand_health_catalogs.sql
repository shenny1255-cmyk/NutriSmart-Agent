-- Mở rộng danh mục chuẩn để người dùng tìm/chọn thay vì phải tự khai báo.
INSERT INTO medical_conditions(name) VALUES
  ('Hen phế quản'),
  ('Bệnh gout'),
  ('Trào ngược dạ dày thực quản'),
  ('Gan nhiễm mỡ'),
  ('Suy giáp'),
  ('Cường giáp'),
  ('Bệnh thận mạn'),
  ('Bệnh phổi tắc nghẽn mạn tính'),
  ('Bệnh mạch vành'),
  ('Thiếu máu'),
  ('Béo phì'),
  ('Rối loạn lo âu')
ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name;

INSERT INTO allergens(name) VALUES
  ('Trứng'),
  ('Cá'),
  ('Đậu nành'),
  ('Hạt cây'),
  ('Hạt mè'),
  ('Lúa mì'),
  ('Thịt gà'),
  ('Thịt bò'),
  ('Latex'),
  ('Bụi nhà'),
  ('Phấn hoa'),
  ('Lông động vật'),
  ('Penicillin'),
  ('Aspirin')
ON CONFLICT (name) DO NOTHING;
