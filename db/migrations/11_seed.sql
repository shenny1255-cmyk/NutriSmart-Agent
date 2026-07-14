INSERT INTO countries(code, name) VALUES
  ('VN','Việt Nam'), ('US','Hoa Kỳ'), ('JP','Nhật Bản');

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