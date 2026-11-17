# Kết quả kiểm tra nhãn RAG

> Ngày kiểm tra: 17/11/2026 12:41
> Người kiểm tra: Nhóm E15 (đối chiếu toàn văn chunk từ DB)
> Phương pháp: chọn ngẫu nhiên 12/51 câu (seed=42, ~23.5%), đối chiếu thủ công toàn văn từng chunk.

## Kết quả tổng hợp

**Đồng thuận: 12/12 câu (100%)**

> Câu trích dẫn cho khóa luận:
> *"Nhãn được gán bởi mô hình AI dựa trên trích dẫn; nhóm kiểm tra ngẫu nhiên 12/51 câu (seed=42) bằng cách đối chiếu toàn văn đoạn tài liệu, đồng thuận 12/12."*

### Lưu ý về phương pháp
- Đánh giá lần đầu (xem 400 ký tự đầu mỗi chunk) cho kết quả 10/12 do chunk 102 và 129 có thông tin nằm sâu hơn trong nội dung.
- Sau khi đọc toàn văn, cả q03 và q14 đều được xác nhận đúng.
- **Phát hiện phụ:** Chunk 102 mở đầu bằng mục lục, nhưng phần thân chứa thông tin hữu ích — không nên lọc sapo một cách mù quáng mà cần phân tích nội dung thực tế. Ghi nhận để xem xét lại chiến lược chunking ở GĐ3.
- **Ghi chú q51:** Trigram định vị đúng bài viết gout (chunk 107) nhưng nDCG@5 = 0 vì chunk 107 không nằm trong top-5 khi hệ thống tính điểm. Nguyên nhân: câu gõ không dấu làm điểm vector giảm mạnh, trigram chỉ bù đắp một phần không đủ để vào top-5. Hướng fix: áp dụng unaccent (migration 13_unaccent.sql đã có sẵn).

## Chi tiết từng câu

| # | ID | Câu hỏi | Chunks | Kết quả | Ghi chú |
|---|---|---|---|---|---|
| 1 | q37 | Thực phẩm nào giàu sắt heme từ động vật? | 129, 130, 132, 133 | ✅ Đồng ý | Chunk 130 trực tiếp đề cập protein động vật. Chunk 133 (nonheme) là nhiễu nhẹ nhưng chấp nhận được |
| 2 | q49 | Chất béo trans có trong thực phẩm nào? | 115 | ✅ Đồng ý | Nội dung đầy đủ: "Trans fat...thực phẩm chế biến công nghiệp có dầu hydrate hóa (chiên rán, thức ăn nhanh, snack, margarine)" |
| 3 | q42 | Dấu hiệu cơ thể bị mất nước là gì? | 152, 153 | ✅ Đồng ý | Chunk 153 nêu triệu chứng nhức đầu đặc trưng khi mất nước |
| 4 | q03 | Người tiểu đường có được ăn trái cây không? | 102, 104, 105 | ✅ Đồng ý | Chunk 102 phần thân: "Người bệnh ĐTĐ nên ăn trái cây và rau quả có lượng calo thấp..." |
| 5 | q02 | GI của gạo lứt so với gạo trắng? | 103, 106 | ✅ Đồng ý | Chunk 103 đề cập tinh bột GI thấp; chunk 106 khuyên thay gạo trắng |
| 6 | q51 | "bi gut co an duoc hai san khong" (không dấu) | 107 | ✅ Đồng ý | Chunk 107 đúng bài gout (tôm, cua trong danh sách cần tránh). Lưu ý: nDCG@5=0 vì chunk không vào top-5 với câu không dấu |
| 7 | q41 | Thực phẩm nào giúp giảm trào ngược axit? | 139, 146 | ✅ Đồng ý | Chunk 139 liệt kê trực tiếp thịt thăn, sữa chua giảm trào ngược |
| 8 | q05 | Acid uric cao có nên uống bia không? | 107 | ✅ Đồng ý | Chunk 107: "Bia và rượu mạnh [cần tránh]" |
| 9 | q09 | Cholesterol LDL cao ăn trứng bao nhiêu quả/tuần? | 115 | ✅ Đồng ý | Chunk 115: "trứng gà toàn phần (600 mg% cholesterol)" + giới hạn <200mg/ngày |
| 10 | q14 | Vitamin C giúp hấp thu sắt như thế nào? | 129, 130, 133, 134 | ✅ Đồng ý | Chunk 134 phần cuối: "ăn thực phẩm giàu sắt cùng thực phẩm chứa nhiều vitamin C...nhằm cải thiện sự hấp thụ sắt" |
| 11 | q18 | Người lớn uống bao nhiêu nước mỗi ngày? | 149, 152 | ✅ Đồng ý | Tiêu đề chunk 152: "Tại sao chúng ta cần uống 2 lít nước mỗi ngày?" |
| 12 | q35 | "tieu duong kieng an gi" (không dấu) | 102, 103, 104, 106 | ✅ Đồng ý | Chunk 104, 106 liệt kê nhóm thực phẩm cần kiêng |
