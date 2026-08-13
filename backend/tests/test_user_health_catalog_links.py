from app.models import UserAllergen, UserMedicalCondition


def test_bang_lien_ket_suc_khoe_co_ten_theo_nguoi_dung():
    assert UserMedicalCondition.__tablename__ == "user_medical_conditions"
    assert UserAllergen.__tablename__ == "user_allergens"


def test_hai_bang_lien_ket_dung_khoa_chinh_kep():
    condition_pk = {column.name for column in UserMedicalCondition.__table__.primary_key}
    allergen_pk = {column.name for column in UserAllergen.__table__.primary_key}

    assert condition_pk == {"user_id", "condition_id"}
    assert allergen_pk == {"user_id", "allergen_id"}


def test_bang_lien_ket_di_ung_khong_con_severity():
    assert "severity" not in UserAllergen.__table__.columns
