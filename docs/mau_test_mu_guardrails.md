# HƯỚNG DẪN VÀ BIỂU MẪU XÂY DỰNG BỘ TEST MÙ (BLIND TEST)
## Đánh giá Hệ thống Cảnh báo An toàn Dinh dưỡng (Warning Engine)
> **Dự án:** NutriSmart Agent - Nhóm E15  
> **Người thực hiện:** Thành viên độc lập trong nhóm (chưa từng đọc từ điển món ăn của hệ thống)  
> **Mục tiêu:** Tạo 30 - 50 ca kiểm thử khách quan, không thiên vị (unbiased), làm bằng chứng khoa học cho Khóa luận Tốt nghiệp.

---

## 1. NGUYÊN TẮC "TEST MÙ" (BLIND EVALUATION)

1. **Tuyệt đối không xem trước code hoặc file dữ liệu:** Bạn KHÔNG mở file `dish_ingredients.json` hoặc `guardrails.py` trong quá trình viết bộ test này.
2. **Dựa trên công thức nấu ăn thực tế của Việt Nam:** Bạn nghĩ ra các món ăn đời thường quen thuộc, bao gồm cả:
   - **Món lộ rõ thành phần:** Ví dụ *"Tôm hấp sả"*, *"Thịt bò xào ớt chuông"*, *"Trứng chiên"*.
   - **Món có thành phần ẩn (dị ứng ẩn / gia vị ẩn):** Ví dụ *"Bún chả"* (chấm nước mắm cá), *"Gỏi gà"* (rắc lạc rang), *"Bánh xèo"* (thường có tôm), *"Bò lúc lắc"* (ướp dầu hào, xì dầu).
3. **Phải có cả ca AN TOÀN (Negative Controls):**
   - Không được chỉ viết toàn món gây hại! Cần có khoảng **30% - 40% món an toàn** để kiểm tra xem hệ thống có bị "báo động giả" (False Positive) hay không.
   - Ví dụ: Người bị dị ứng hải sản ăn *"Rau muống luộc"* hoặc *"Thịt heo nướng"* $\rightarrow$ Kỳ vọng: **KHÔNG CẢNH BÁO**.

---

## 2. DANH MỤC HỆ THỐNG HỖ TRỢ

Khi gán nhãn, bạn chỉ chọn các Nhóm dị ứng hoặc Bệnh nền nằm trong danh sách chuẩn dưới đây:

### A. Nhóm Dị ứng Thực phẩm
1. **Hải sản có vỏ** (tôm, cua, ghẹ, ốc, mực, nghêu, sò, hàu, mắm tôm, mắm ruốc...)
2. **Cá** (cá sông, cá biển, chả cá, nước mắm cá...)
3. **Đậu phộng / Lạc** (đậu phộng luộc, lạc rang, bơ đậu phộng, kẹo lạc...)
4. **Đậu nành** (đậu phụ, đậu hũ, sữa đậu nành, tương, xì dầu / nước tương...)
5. **Trứng** (trứng gà, trứng vịt, bánh flan, sốt mayonnaise...)
6. **Sữa bò** (sữa tươi, sữa đặc, phô mai, bơ, sữa chua...)
7. **Lúa mì / Gluten** (bánh mì, mì tôm, mì sợi, bột mì, bánh bông lan...)
8. **Mè / Vừng** (hạt mè, dầu mè, sốt mè rang...)
9. **Hạt cây** (hạt điều, hạt óc chó, hạnh nhân, hạt dẻ...)

### B. Nhóm Bệnh nền Mạn tính
1. **Bệnh Gút (Gout) / Tăng acid uric:** Kiêng purin cao (nội tạng động vật, hải sản có vỏ, thịt đỏ, rượu bia).
2. **Đái tháo đường típ 2 (Tiểu đường):** Kiêng đường đơn, món ngọt (chè, nước ngọt có ga, bánh kẹo, trà sữa, thực phẩm GI cao).
3. **Tăng huyết áp (Cao huyết áp):** Kiêng mặn (nhiều muối, nước mắm chấm đậm, dưa muối, cà muối, khô cá, mắm nêm, đồ kho đậm vị).
4. **Rối loạn lipid máu (Mỡ máu cao / Cholesterol cao):** Kiêng chất béo bão hòa, đồ chiên xào ngập dầu, nội tạng động vật, da gà/vịt, mỡ heo.
5. **Bệnh thận mạn / Suy thận:** Cần kiểm soát lượng đạm cao, hạn chế natri, kali, phospho.

---

## 3. BẢNG MẪU ĐIỀN TEST CASE (30 - 50 CÂU)

Bạn hãy điền vào bảng dưới đây (hoặc sao chép ra Excel điền rồi dán ngược lại):

* **Kỳ vọng:** Ghi `CÓ` (nếu món này nguy hiểm với người đó) hoặc `KHÔNG` (nếu món này an toàn).

| STT | Tên món ăn tiếng Việt | Tình trạng của người ăn (Dị ứng hoặc Bệnh nền) | Kỳ vọng cảnh báo (CÓ / KHÔNG) | Giải thích thực tế (Vì sao nguy hiểm hoặc vì sao an toàn) |
|:---:|:---|:---|:---:|:---|
| *Mẫu 1* | *Gỏi cuốn tôm thịt* | *Dị ứng: Hải sản có vỏ* | *CÓ* | *Trong gỏi cuốn có nguyên con tôm luộc.* |
| *Mẫu 2* | *Gà hấp hành* | *Dị ứng: Hải sản có vỏ* | *KHÔNG* | *Thịt gà và hành lá, hoàn toàn không có hải sản.* |
| *Mẫu 3* | *Bánh cuốn chả quế* | *Dị ứng: Cá* | *CÓ* | *Nước chấm bánh cuốn pha từ nước mắm cá.* |
| *Mẫu 4* | *Chè trôi nước ngọt* | *Bệnh nền: Đái tháo đường* | *CÓ* | *Chứa lượng đường đơn rất cao từ mật mía/đường.* |
| *Mẫu 5* | *Bí xanh luộc* | *Bệnh nền: Tăng huyết áp* | *KHÔNG* | *Món luộc thanh đạm, không ướp muối.* |
| 1 | Bún bò Huế | Hải sản có vỏ | CÓ | Nước dùng bún bò Huế truyền thống bắt buộc nêm mắm ruốc Huế (chế biến từ con ruốc/tép biển thuộc nhóm giáp xác có vỏ). |
| 2 | Thịt ba chỉ luộc chấm nước mắm tỏi ớt | Hải sản có vỏ | KHÔNG | Chỉ gồm thịt heo luộc và nước mắm làm từ cá, hoàn toàn không chứa tôm, cua, ốc hay động vật có vỏ. |
| 3 | Phở bò tái nạm | Cá | CÓ | Dù nguyên liệu chính là thịt bò nhưng nước dùng phở truyền thống luôn nêm nước mắm cá cốt để dậy mùi thơm đặc trưng. |
| 4 | Gỏi ngó sen tôm thịt | Đậu phộng | CÓ | Món gỏi miền Nam truyền thống luôn rắc đậu phộng rang giã dập lên bề mặt để tạo độ bùi béo. |
| 5 | Canh khổ qua nhồi thịt | Đậu phộng | KHÔNG | Món canh làm từ khổ qua, thịt heo băm, nấm mèo và hành lá, không sử dụng đậu phộng trong chế biến. |
| 6 | Bò lúc lắc | Đậu nành | CÓ | Công thức ướp thịt bò lúc lắc truyền thống luôn dùng nước tương (xì dầu làm từ đậu nành) và dầu hào để làm mềm và đậm vị thịt. |
| 7 | Cơm tấm sườn bì chả | Trứng | CÓ | Miếng chả trứng hấp đặc trưng trong dĩa cơm tấm được làm từ trứng vịt/trứng gà đánh tan hấp cùng thịt băm và bún tàu. |
| 8 | Phở gà ta | Sữa bò | KHÔNG | Món nước truyền thống nấu từ xương gà, thịt gà, bánh phở gạo và rau thơm, không chứa sữa bò hay chế phẩm từ sữa. |
| 9 | Bánh flan caramen | Sữa bò | CÓ | Món tráng miệng phổ biến được chế biến trực tiếp từ hỗn hợp sữa tươi, sữa đặc có đường và trứng gà. |
| 10 | Bánh mì thịt nướng | Gluten | CÓ | Vỏ bánh mì Việt Nam được làm từ bột mì chứa hàm lượng gluten cao. |
| 11 | Bánh đúc lá dứa | Gluten | KHÔNG | Bánh đúc miền Nam được khuấy từ bột gạo tẻ, bột năng và nước cốt lá dứa, hoàn toàn không chứa bột mì hay gluten. |
| 12 | Hến xúc bánh đa | Mè | CÓ | Bánh đa nướng ăn kèm hến xào đặc sản miền Trung luôn được phủ nhiều hạt mè (vừng) rang trên bề mặt bánh. |
| 13 | Bánh trung thu thập cẩm | Hạt cây | CÓ | Nhân bánh thập cẩm truyền thống luôn có hạt điều (thuộc nhóm hạt cây) trộn cùng mứt bí, lạp xưởng và mỡ đường. |
| 14 | Canh bầu nấu thịt băm | Bệnh Gút | KHÔNG | Bầu thuộc nhóm rau củ có hàm lượng purin rất thấp, kết hợp lượng nhỏ thịt heo nạc băm nên an toàn cho người bệnh Gút. |
| 15 | Lẩu lòng bò | Bệnh Gút | CÓ | Nội tạng động vật (lòng, gan, lá lách) và nước hầm thịt đỏ chứa hàm lượng nhân purin cực cao, dễ kích phát cơn gút cấp. |
| 16 | Xôi mặn thập cẩm | Đái tháo đường típ 2 | CÓ | Gạo nếp có chỉ số đường huyết (GI) rất cao, dễ gây tăng vọt đường huyết sau ăn ở người đái tháo đường típ 2. |
| 17 | Cá diêu hồng hấp gừng hành | Đái tháo đường típ 2 | KHÔNG | Món hấp giàu đạm lành mạnh, ít tinh bột và không chứa đường đơn, giúp ổn định đường huyết. |
| 18 | Cá kho tộ | Tăng huyết áp | CÓ | Món kho truyền thống miền Nam nêm nhiều nước mắm, muối và nước màu để kho kẹo, chứa lượng natri rất cao gây tăng huyết áp. |
| 19 | Bông cải xanh luộc | Tăng huyết áp | KHÔNG | Rau xanh luộc thanh đạm, không nêm muối hay gia vị mặn, lại giàu kali tự nhiên có lợi cho việc kiểm soát huyết áp. |
| 20 | Cháo lòng tiết canh | Rối loạn lipid máu | CÓ | Lòng heo, dồi trường, tim gan và tiết chứa hàm lượng cholesterol cùng chất béo bão hòa rất cao, làm nặng thêm tình trạng mỡ máu. |
| 21 | Bún đậu mắm tôm | Hải sản có vỏ | CÓ | Chấm kèm mắm tôm lên men từ con moi/tép biển (giáp xác có vỏ), gây phản ứng dị ứng nghiêm trọng. |
| 22 | Gà nướng muối ớt | Cá | KHÔNG | Nguyên liệu gồm thịt gà ướp muối, ớt, sả, tỏi và dầu ăn, không sử dụng cá hay nước mắm cá. |
| 23 | Canh chua cá lóc | Cá | CÓ | Thành phần chính là cá lóc đồng và thường nêm thêm nước mắm cá để tạo vị đậm đà. |
| 24 | Bánh tráng trộn | Đậu phộng | CÓ | Món ăn vặt đường phố luôn trộn kèm đậu phộng rang giã dập cùng muối tôm, khô bò và rau răm. |
| 25 | Cơm gà xé phay Hội An | Đậu nành | KHÔNG | Gồm cơm nấu nước luộc gà, thịt gà ta xé, hành tây, rau răm và nước mắm chua ngọt, không dùng đậu nành hay nước tương. |
| 26 | Đậu hũ nhồi thịt sốt cà chua | Đậu nành | CÓ | Thành phần chính là đậu hũ (đậu phụ) được chế biến trực tiếp từ hạt đậu nành. |
| 27 | Canh bí đỏ hầm xương | Trứng | KHÔNG | Món canh gia đình nấu từ bí đỏ và xương sườn heo, hoàn toàn không có thành phần trứng. |
| 28 | Bánh mì chảo thập cẩm | Trứng | CÓ | Suất ăn sáng phổ biến này luôn có trứng gà ốp la đi kèm cùng pate, xúc xích và xíu mại. |
| 29 | Bánh mì bơ tỏi phô mai | Sữa bò | CÓ | Chứa phô mai tan chảy và bơ động vật, đều là chế phẩm trực tiếp từ sữa bò. |
| 30 | Mì hoành thánh | Gluten | CÓ | Cả sợi mì tươi và lớp vỏ bánh hoành thánh đều được cán từ bột mì giàu gluten. |
| 31 | Canh chua cá diêu hồng | Mè | KHÔNG | Canh chua nấu từ cá diêu hồng, cà chua, thơm (dứa), bạc hà và rau om, không sử dụng hạt mè hay dầu mè. |
| 32 | Bánh rán ngọt phủ vừng | Mè | CÓ | Lớp vỏ bánh rán truyền thống miền Bắc được áo một lớp vừng (mè) trắng rang thơm bên ngoài. |
| 33 | Bò kho bánh mì | Hạt cây | KHÔNG | Bò kho nấu từ thịt bò, cà rốt, sả, hoa hồi, quế và ăn kèm bánh mì bột mì, không chứa các loại hạt cây như hạt điều hay hạnh nhân. |
| 34 | Gà xào hạt điều | Hạt cây | CÓ | Món xào này sử dụng trực tiếp hạt điều (thuộc nhóm hạt cây gây dị ứng) đảo cùng thịt gà và rau củ. |
| 35 | Ốc len xào dừa | Bệnh Gút | CÓ | Hải sản có vỏ như ốc len chứa nhiều nhân purin làm tăng nhanh nồng độ acid uric trong máu. |
| 36 | Chè đậu xanh nước cốt dừa | Đái tháo đường típ 2 | CÓ | Chè nấu với lượng lớn đường tinh luyện kết hợp tinh bột đậu xanh làm tăng đường huyết sau ăn rất nhanh. |
| 37 | Cà pháo muối chua chấm mắm tôm | Tăng huyết áp | CÓ | Cà muối nén và mắm tôm đều có hàm lượng muối (natri) cực kỳ cao, chống chỉ định với người tăng huyết áp. |
| 38 | Ức gà áp chảo | Rối loạn lipid máu | KHÔNG | Ức gà bỏ da chứa rất ít chất béo bão hòa và cholesterol, phù hợp cho thực đơn kiểm soát mỡ máu. |
| 39 | Cơm chiên dương châu | Rối loạn lipid máu | CÓ | Cơm được chiên đảo nhiều dầu mỡ cùng lạp xưởng, chả lụa và trứng, giàu chất béo bão hòa và năng lượng. |
| 40 | Mắm chưng thịt hột vịt | Bệnh thận mạn | CÓ | Món mắm chưng miền Nam chứa lượng muối (natri) cực cao cùng nhiều đạm và phospho từ mắm cá, thịt heo và trứng vịt, gây quá tải cho thận. |

---

## 4. HƯỚNG DẪN SAU KHI ĐIỀN XONG

1. Bạn chỉ cần gửi lại file này (hoặc file Excel tương ứng).
2. Nhóm sẽ chạy script đánh giá tự động:
   - Hệ thống sẽ chạy Warning Engine trên danh sách món bạn vừa viết.
   - So khớp kết quả của AI/Rule với cột **Kỳ vọng** của bạn.
   - Tính ra **Recall** (bắt trúng bao nhiêu ca nguy hiểm) và **Precision** (có bị báo nhầm ca an toàn nào không).
3. Kết quả đo được sẽ được chụp biểu đồ và đưa thẳng vào **Chương Thực nghiệm của Khóa luận Tốt nghiệp**.
