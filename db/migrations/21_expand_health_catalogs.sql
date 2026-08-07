-- Mở rộng danh mục chuẩn để người dùng tìm/chọn thay vì phải tự khai báo.
INSERT INTO medical_conditions(code, name) VALUES
  ('J45',   'Hen phế quản'),
  ('M10',   'Bệnh gout'),
  ('K21',   'Trào ngược dạ dày thực quản'),
  ('K76.0', 'Gan nhiễm mỡ'),
  ('E03',   'Suy giáp'),
  ('E05',   'Cường giáp'),
  ('N18',   'Bệnh thận mạn'),
  ('J44',   'Bệnh phổi tắc nghẽn mạn tính'),
  ('I25',   'Bệnh mạch vành'),
  ('D64',   'Thiếu máu'),
  ('E66',   'Béo phì'),
  ('F41',   'Rối loạn lo âu')
ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name;

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
