# Nguồn tham khảo của Warning Engine và ngưỡng đánh giá — tình trạng kiểm chứng

Tra cứu ngày 14/11/2026. "Đã xác minh" = xác nhận được số hiệu, ngày ban hành, tên văn bản
qua cơ sở dữ liệu văn bản (caselaw.vn, luatvietnam.vn, vnras.com…), **chưa** phải đã đọc
nội dung chuyên môn trong bản gốc. Trước khi trích vào khóa luận, nhóm cần mở bản gốc và
ghi số trang/mục cụ thể.

| Rule / ngưỡng | Nguồn | Tình trạng | Việc còn phải làm |
|---|---|---|---|
| Đái tháo đường típ 2 | QĐ **5481/QĐ-BYT** ngày 30/12/2020 (thay QĐ 3319/2017; sửa đổi bởi QĐ 1353/QĐ-BYT ngày 23/02/2021) | Đã xác minh số hiệu | Trích mục dinh dưỡng (hạn chế đường đơn, GI) |
| Tăng huyết áp | QĐ **3192/QĐ-BYT** ngày 31/08/2010 | Đã xác minh số hiệu; không tìm thấy văn bản thay thế | Kiểm tra hiệu lực trên vbpl.vn; trích mục giảm muối |
| Giới hạn muối | WHO Fact sheet *Salt reduction*: người lớn < 5 g muối (< 2.000 mg natri)/ngày | Đã xác minh | — |
| Gout | QĐ **361/QĐ-BYT** ngày 25/01/2014 (Hướng dẫn chẩn đoán và điều trị các bệnh cơ xương khớp) | Xác minh được văn bản; **chưa xác nhận được có chương Bệnh gút** | Mở bản PDF, tìm chương gút; nếu không có thì thay nguồn |
| Rối loạn lipid máu | Hội Tim mạch học Quốc gia Việt Nam — Khuyến cáo chẩn đoán và điều trị RLLM (2015) | Chỉ thấy qua trích dẫn thứ cấp | Tìm bản gốc; kiểm tra có bản cập nhật sau 2015 không |
| Gan nhiễm mỡ | Viện Dinh dưỡng Quốc gia (chung chung) | **Chưa xác minh** | Tìm khuyến cáo cụ thể (VD Hội Gan mật VN) |
| Bệnh thận mạn | QĐ **2388/QĐ-BYT** ngày 12/08/2024 (Hướng dẫn chẩn đoán và điều trị bệnh thận mạn và một số bệnh lý thận) — mới hơn QĐ 3931/QĐ-BYT ngày 21/09/2015 | Đã xác minh số hiệu | Trích mục kiểm soát kali/phospho/đạm |
| Calo tối thiểu nữ 1.200 / nam 1.500 | 2013 AHA/ACC/TOS Guideline for the Management of Overweight and Obesity in Adults: chế độ 1.200–1.500 kcal/ngày (nữ), 1.500–1.800 (nam) | Thấy qua bảng trên PubMed Central (PMC5819889); cần đối chiếu bản gốc | Trích dẫn đầy đủ bài báo gốc (Jensen et al., *Circulation* 2014) |
| Giảm cân an toàn | NHLBI (NIH): 1–2 lb/tuần (~0,5–1 kg/tuần), thâm hụt 500–1.000 kcal/ngày | Đã xác minh | Dùng cho mục 2.4.3 (ngưỡng `LOSE_WEIGHT ≤ −0,3 kg/tuần`) |

## Giải thích ngưỡng cân nặng trong `plan_evaluator.py` (mục 2.4.3)

- `LOSE_WEIGHT: Δ ≤ −0,3 kg/tuần` — thấp hơn mức an toàn 0,5–1 kg/tuần của NHLBI vì
  chu kỳ chỉ 7 ngày, cân nặng dao động trong ngày do nước/khối lượng ăn uống có thể tới
  1–2 kg, nên mốc tối thiểu thấp hơn để tránh kết luận "KHÔNG ĐẠT" do nhiễu.
- `MAINTAIN / MEDICAL: |Δ| ≤ 0,7 kg/tuần` — biên chịu nhiễu cho mục tiêu giữ cân.
- `GAIN_MUSCLE: Δ ≥ 0,2 kg/tuần` — tăng cơ chậm hơn giảm mỡ.
- Cả ba mốc là lựa chọn thiết kế (chưa có thực nghiệm). Nếu hội đồng hỏi, trả lời theo
  lập luận nhiễu cân nặng ở trên và đề xuất hiệu chỉnh khi có dữ liệu người dùng thật.

## Liên kết đã dùng khi tra cứu

- QĐ 5481/QĐ-BYT: https://caselaw.vn/van-ban-phap-luat/369321-quyet-dinh-so-5481-qd-byt-ngay-30-12-2020-ve-tai-lieu-chuyen-mon-huong-dan-chan-doan-va-dieu-tri-dai-thao-duong-tip-2-ban-hanh-boi-bo-truong-bo-y-te
- QĐ 1353/QĐ-BYT: https://caselaw.vn/van-ban-phap-luat/366815-quyet-dinh-so-1353-qd-byt-ngay-23-02-2021-sua-doi-huong-dan-chan-doan-va-dieu-tri-dai-thao-duong-tip-2-tai-quyet-dinh-5481-qd-byt-ban-hanh-boi-bo-y-te
- QĐ 3192/QĐ-BYT: https://luatvietnam.vn/y-te/quyet-dinh-3192-qd-byt-bo-y-te-84669-d1.html
- QĐ 361/QĐ-BYT: https://vnras.com/huong-dan-chan-doan-va-dieu-tri-cac-benh-co-xuong-khop-theo-bo-y-te-quyet-dinh-so-361-qd-byt-ngay-25-01-2014/
- QĐ 3931/QĐ-BYT: https://vnras.com/huong-dan-chan-doan-va-dieu-tri-mot-so-benh-ve-than-tiet-nieu-theo-bo-y-te-quyet-dinh-so-3931-qd-byt-ngay-21-09-2015/
- QĐ 2388/QĐ-BYT: https://vnras.com/huong-dan-chan-doan-va-dieu-tri-benh-than-man-va-mot-so-benh-ly-than-theo-bo-y-te-quyet-dinh-so-2388-qd-byt-ngay-12-08-2024/
- WHO Salt reduction: https://www.who.int/news-room/fact-sheets/detail/salt-reduction
- AHA/ACC/TOS 2013 (bảng trên PMC): https://pmc.ncbi.nlm.nih.gov/articles/PMC5819889/table/T4
- NHLBI Aim for a Healthy Weight: https://internet-prod.nhlbi.nih.gov/sites/default/files/publications/AimforaHealthyWeightBooklet-020314.epub
