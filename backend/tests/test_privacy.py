"""Test ẩn danh hóa dữ liệu trước khi gửi ra AI cloud (kế hoạch ĐATN v2, mục 3).

Theo Nghị định 13/2023/NĐ-CP, dữ liệu sức khỏe là dữ liệu cá nhân nhạy cảm: không gửi tên,
email, số điện thoại ra nhà cung cấp bên ngoài; tuổi chỉ gửi theo khoảng.
"""
from app.services import privacy


def _sys(content):
    return [{"role": "system", "content": content}]


def test_bo_ho_ten_nguoi_dung():
    msgs = _sys("Trợ lý dinh dưỡng.\nBạn đang trò chuyện với Nguyễn Văn An.\nHồ sơ người dùng:")
    out, report = privacy.anonymize_messages(msgs, full_name="Nguyễn Văn An")
    assert "Nguyễn Văn An" not in out[0]["content"]
    assert report["name"] >= 1


def test_ho_ten_xuat_hien_trong_tin_nhan_nguoi_dung_cung_bi_thay():
    msgs = [{"role": "user", "content": "Tôi là nguyễn văn an, 30 tuổi"}]
    out, _ = privacy.anonymize_messages(msgs, full_name="Nguyễn Văn An")
    assert "nguyễn văn an" not in out[0]["content"].lower()
    assert "người dùng" in out[0]["content"]


def test_thay_email_va_so_dien_thoai():
    msgs = [{"role": "user", "content": "Liên hệ an.nguyen@gmail.com hoặc 0912 345 678, +84987654321"}]
    out, report = privacy.anonymize_messages(msgs)
    text = out[0]["content"]
    assert "gmail.com" not in text and "0912" not in text and "987654321" not in text
    assert "[email]" in text and "[số điện thoại]" in text
    assert report["email"] == 1 and report["phone"] == 2


def test_tuoi_chinh_xac_doi_thanh_khoang():
    out, report = privacy.anonymize_messages(_sys("- Giới tính: MALE · Tuổi: 27 · Cao 170cm"))
    assert "Tuổi: 25-34" in out[0]["content"]
    assert "27" not in out[0]["content"]
    assert report["age"] == 1


def test_khoang_tuoi_bien():
    assert privacy.age_band(17) == "dưới 18"
    assert privacy.age_band(18) == "18-24"
    assert privacy.age_band(64) == "55-64"
    assert privacy.age_band(70) == "65+"


def test_giu_nguyen_du_lieu_can_cho_tu_van():
    # Bệnh nền, dị ứng, chiều cao, cân nặng cần để tư vấn → giữ (tối thiểu hóa, không xóa hết)
    msgs = _sys("- Cao 170cm · Nặng 68kg\n- Bệnh nền: Bệnh gout · Dị ứng: Đậu phộng")
    out, report = privacy.anonymize_messages(msgs)
    assert out[0]["content"] == msgs[0]["content"]
    assert sum(report.values()) == 0


def test_khong_sua_messages_goc():
    msgs = [{"role": "user", "content": "email a@b.vn"}]
    privacy.anonymize_messages(msgs)
    assert msgs[0]["content"] == "email a@b.vn"


def test_so_lieu_dinh_duong_khong_bi_nham_la_so_dien_thoai():
    msgs = [{"role": "user", "content": "Mục tiêu 2007 kcal, 4700 mg kali, năm 2024"}]
    out, report = privacy.anonymize_messages(msgs)
    assert out[0]["content"] == msgs[0]["content"]
    assert report["phone"] == 0
