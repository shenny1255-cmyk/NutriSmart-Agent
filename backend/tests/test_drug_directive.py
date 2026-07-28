"""Chỉ thị ràng buộc dược phẩm chỉ được chèn khi câu hỏi thực sự về thuốc.

Trước đây chỉ thị này gắn vào MỌI câu hỏi và đứng cuối prompt (vị trí mạnh nhất),
ra lệnh "GHI ĐÈ lên mọi tài liệu tham khảo RAG" → hỏi chuyện dinh dưỡng thì trợ lý
từ chối dùng tài liệu vừa truy hồi, dù truy hồi đúng.
"""
from app.services.nutrition_context import lien_quan_den_thuoc, render_drug_directive

QUY_DINH = [
    {"drug_name": "Sibutramine", "active_ingredient": "Sibutramine",
     "country_code": "VN", "country_name": "Việt Nam", "status": "BANNED", "note": None},
    {"drug_name": "Paracetamol", "active_ingredient": "Paracetamol",
     "country_code": "VN", "country_name": "Việt Nam", "status": "ALLOWED", "note": None},
]


# ---------- Câu hỏi VỀ thuốc ----------

def test_hoi_dich_danh_ten_thuoc():
    assert lien_quan_den_thuoc("Sibutramine có bị cấm ở Việt Nam không?", QUY_DINH) is True


def test_khong_phan_biet_hoa_thuong():
    assert lien_quan_den_thuoc("paracetamol uống được không", QUY_DINH) is True


def test_tu_khoa_chung_ve_thuoc():
    assert lien_quan_den_thuoc("Tôi có nên dùng thuốc giảm cân không?", QUY_DINH) is True
    assert lien_quan_den_thuoc("Loại này có cần kê đơn không?", QUY_DINH) is True


# ---------- Câu hỏi KHÔNG về thuốc ----------

def test_cau_hoi_dinh_duong_thuan_tuy():
    assert lien_quan_den_thuoc("Chế độ ăn DASH cho người tăng huyết áp là gì?", QUY_DINH) is False
    assert lien_quan_den_thuoc("Người bị gout nên kiêng ăn gì?", QUY_DINH) is False
    assert lien_quan_den_thuoc("Một tô phở bò bao nhiêu calo?", QUY_DINH) is False


def test_tin_nhan_rong():
    assert lien_quan_den_thuoc("", QUY_DINH) is False
    assert lien_quan_den_thuoc(None, QUY_DINH) is False


def test_khong_co_quy_dinh_nao_van_bat_duoc_tu_khoa_chung():
    assert lien_quan_den_thuoc("thuốc này uống sao", []) is True
    assert lien_quan_den_thuoc("ăn gì cho khỏe", []) is False


# ---------- Khối chỉ thị ----------

def test_khong_lien_quan_thi_khong_chen_chi_thi():
    assert render_drug_directive("Người bị gout nên kiêng ăn gì?", QUY_DINH) == ""


def test_lien_quan_thi_giu_nguyen_rang_buoc_cu():
    khoi = render_drug_directive("Sibutramine có bị cấm không?", QUY_DINH)
    assert "QUY TẮC BẮT BUỘC VỀ QUY ĐỊNH DƯỢC PHẨM" in khoi
    # 3 trạng thái của task 9 phải còn nguyên
    assert "ALLOWED" in khoi and "RESTRICTED" in khoi and "BANNED" in khoi
