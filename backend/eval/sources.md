# Nguồn tham khảo của Warning Engine và ngưỡng đánh giá - tình trạng kiểm chứng

Tra cứu và cập nhật hoàn thiện ngày 18/11/2026. Tất cả số hiệu văn bản và tài liệu gốc đã được xác minh.

| Rule / ngưỡng | Nguồn | Tình trạng | Chi tiết nội dung chuyên môn |
|---|---|---|---|
| Đái tháo đường típ 2 | QĐ **5481/QĐ-BYT** ngày 30/12/2020 (sửa đổi bởi QĐ 1353/QĐ-BYT ngày 23/02/2021) | Đã xác minh | Phần dinh dưỡng: Khuyến cáo hạn chế carbohydrate có chỉ số đường huyết (GI) cao và đường hấp thu nhanh (đường đơn); ưu tiên ngũ cốc nguyên hạt, rau xanh và trái cây ít ngọt. |
| Tăng huyết áp | QĐ **3192/QĐ-BYT** ngày 31/08/2010 (Bộ Y tế) | Đã xác minh | Hướng dẫn điều trị không dùng thuốc: Giảm lượng muối ăn vào (< 5-6 g muối/ngày); hạn chế đồ ăn mặn, dưa cà muối, mắm nêm, nước chấm mặn. |
| Giới hạn muối | WHO Fact sheet *Salt reduction* (WHO 2023) | Đã xác minh | Khuyến nghị lượng muối tiêu thụ hàng ngày cho người trưởng thành: < 5 g muối / ngày (tương đương < 2.000 mg natri / ngày). |
| Gout | QĐ **361/QĐ-BYT** ngày 25/01/2014 (Bộ Y tế) | Đã xác minh | Tài liệu "Hướng dẫn chẩn đoán và điều trị các bệnh cơ xương khớp", bài **Bệnh gút**: Chế độ ăn hạn chế thực phẩm nhiều purin (phủ tạng động vật, thịt đỏ, hải sản có vỏ), kiêng rượu bia, uống nhiều nước. |
| Rối loạn lipid máu | Hội Tim mạch học Quốc gia Việt Nam (VNHA 2015 & cập nhật VNHA 2024) | Đã xác minh | Khuyến cáo chẩn đoán và điều trị rối loạn lipid máu: Thay đổi lối sống là nền tảng; hạn chế chất béo bão hòa (< 7% năng lượng), chất béo chuyển hóa (trans-fat), nội tạng động vật; tăng chất xơ hòa tan. |
| Gan nhiễm mỡ | Hội Gan mật Việt Nam (VASLD) & Hội Gan Mật TP.HCM (HASLD) | Đã xác minh | Hướng dẫn chẩn đoán và quản lý bệnh gan nhiễm mỡ liên quan chuyển hóa (MASLD/NAFLD): Giảm 5-10% thể trọng nếu thừa cân, hạn chế tối đa đường tinh luyện (fructose, nước ngọt), giảm mỡ bão hòa, kiêng tuyệt đối rượu bia. |
| Bệnh thận mạn | QĐ **2388/QĐ-BYT** ngày 12/08/2024 (Bộ Y tế) | Đã xác minh | Hướng dẫn chẩn đoán và điều trị bệnh thận mạn: Điều chỉnh lượng đạm theo giai đoạn suy thận, kiểm soát natri, kali và phospho để tránh tăng áp lực lọc cầu thận. |
| Calo tối thiểu nữ 1.200 / nam 1.500 | 2013 AHA/ACC/TOS Guideline for the Management of Overweight and Obesity in Adults (*Circulation* 2014) | Đã xác minh | Trích dẫn: Jensen MD, et al. *Circulation*. 2014;129(25 Suppl 2):S102-S138. Chế độ ăn giảm calo an toàn thường khuyến nghị 1.200-1.500 kcal/ngày cho nữ và 1.500-1.800 kcal/ngày cho nam để tránh suy kiệt. |
| Giảm cân an toàn | National Heart, Lung, and Blood Institute (NHLBI / NIH) | Đã xác minh | Khuyến nghị mức giảm cân an toàn bền vững: 1-2 lb/tuần (~0,5-1 kg/tuần), tương đương thâm hụt năng lượng 500-1.000 kcal/ngày. |

## Giải thích ngưỡng cân nặng trong `plan_evaluator.py` (mục 2.4.3)

- `LOSE_WEIGHT: Δ ≤ −0,3 kg/tuần` - thấp hơn mức an toàn 0,5-1 kg/tuần của NHLBI vì chu kỳ đánh giá ngắn (chỉ 7 ngày), cân nặng dao động tự nhiên trong ngày do nước/thức ăn có thể tới 1-2 kg, nên mốc tối thiểu hạ nhẹ để tránh phán đoán "KHÔNG ĐẠT" do nhiễu sinh lý.
- `MAINTAIN / MEDICAL: |Δ| ≤ 0,7 kg/tuần` - biên chịu nhiễu sinh lý cho mục tiêu giữ cân hoặc bệnh lý.
- `GAIN_MUSCLE: Δ ≥ 0,2 kg/tuần` - tốc độ tăng khối lượng cơ chậm hơn nhiều so với giảm mỡ.
