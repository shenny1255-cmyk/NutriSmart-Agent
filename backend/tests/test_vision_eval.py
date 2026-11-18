"""GĐ3: bộ đo MAE khẩu phần và learning curve few-shot. Không gọi Gemini thật."""
import csv

import pytest

from app.services import vision_eval as ve

HEADER = ["image_file", "dish_name", "component_name", "actual_grams", "note", "gt_source", "weighed_by",
          "weighed_at", "plate_id", "kcal_per_100g"]


def _csv(path, rows, header=HEADER):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _row(image="a.jpg", name="Cơm trắng", grams=200, **extra):
    return {"image_file": image, "dish_name": "Cơm gà", "component_name": name, "actual_grams": grams, "note": "",
            "gt_source": "WEIGHED", "weighed_by": "Nhóm E15", "weighed_at": "2026-11-20", "plate_id": "",
            "kcal_per_100g": "130", **extra}


def _plate(image, dish="Cơm gà", grams=200.0, density=100.0, plate_id=None):
    return ve.Plate(image_file=image, plate_id=plate_id or image, dish_name=dish, weighed=True, components=[
        ve.ActualComponent(name="Cơm trắng", grams=grams, kcal_per_100g=density)])


def _pred(grams, density=100.0, name="Cơm trắng"):
    return [{"name": name, "grams": grams, "per_100g": {"energy_kcal": density}}]


def test_file_khung_do_ai_sinh_khong_duoc_coi_la_da_can(tmp_path):
    path = _csv(tmp_path / "gt.csv", [_row()], ["image_file", "dish_name", "component_name", "actual_grams", "note"])
    plates = ve.load_ground_truth(path)
    assert plates[0].weighed is False


def test_dong_da_can_phai_co_nguoi_can_va_ngay_can(tmp_path):
    assert ve.load_ground_truth(_csv(tmp_path / "ok.csv", [_row()]))[0].weighed is True
    assert ve.load_ground_truth(_csv(tmp_path / "no.csv", [_row(weighed_by="")]))[0].weighed is False


def test_mot_dong_chua_can_lam_ca_dia_bi_loai(tmp_path):
    rows = [_row(), _row(name="Thịt gà", gt_source="AI_DRAFT")]
    assert ve.load_ground_truth(_csv(tmp_path / "gt.csv", rows))[0].weighed is False


def test_gram_khong_hop_le_bi_tu_choi(tmp_path):
    with pytest.raises(ValueError, match="actual_grams"):
        ve.load_ground_truth(_csv(tmp_path / "gt.csv", [_row(grams=0)]))


def test_cong_chan_du_lieu_chua_can_va_thieu_co_mau(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x")
    plates = [ve.Plate("a.jpg", "a.jpg", "Cơm", False, [ve.ActualComponent("Cơm", 100.0, 130.0)])]
    report = ve.audit_dataset(plates, tmp_path)
    assert any("chưa có số cân thật" in b for b in report["blocking"])
    assert any("tối thiểu" in b for b in report["blocking"])


def test_cong_chan_thieu_file_anh(tmp_path):
    report = ve.audit_dataset([_plate("mat.jpg")], tmp_path)
    assert any("mat.jpg" in b for b in report["blocking"])


def test_sai_so_dia_tinh_theo_tong_gram_va_kcal():
    err = ve.plate_error(_plate("a.jpg", grams=200.0, density=100.0), _pred(150.0, density=120.0))
    assert err["grams_abs"] == 50.0 and err["kcal_actual"] == 200.0
    assert err["kcal_abs"] == pytest.approx(20.0)


def test_khong_co_mat_do_kcal_thi_khong_tu_doan():
    plate = ve.Plate("a.jpg", "a.jpg", "Cơm", True, [ve.ActualComponent("Món lạ", 100.0, None)])
    assert ve.plate_error(plate, _pred(100.0))["kcal_abs"] is None


def test_ghep_thanh_phan_theo_ten_gan_giong_va_tinh_ca_phan_thieu_thua():
    actual = [ve.ActualComponent("Cơm trắng", 200.0, 130.0), ve.ActualComponent("Trứng ốp la", 50.0, 190.0)]
    out = ve.component_errors(actual, _pred(180.0, name="Cơm") + _pred(30.0, name="Dưa leo"))
    assert out["matched"] == 1 and out["missed"] == 1 and out["extra"] == 1
    assert sorted(out["abs_errors"]) == [20.0, 30.0, 50.0]


def test_mae_va_wape():
    assert ve.mae([10.0, 30.0]) == 20.0
    assert ve.wape([10.0, 30.0], [100.0, 100.0]) == pytest.approx(0.2)


def test_khoang_tin_cay_bootstrap_on_dinh_theo_seed():
    values = [float(v) for v in range(1, 31)]
    first = ve.bootstrap_ci(values, seed=7)
    assert first == ve.bootstrap_ci(values, seed=7)
    assert first[0] < ve.mae(values) < first[1]


def test_so_sanh_cap_phat_hien_giam_that():
    base = [100.0 + i for i in range(30)]
    result = ve.paired_comparison(base, [v - 40.0 for v in base], seed=1)
    assert result["mean_diff"] == pytest.approx(-40.0) and result["improved"] == 30
    assert result["p_value"] < 0.001 and result["ci"][1] < 0


def test_khong_co_khac_biet_thi_khong_ket_luan_giam():
    base = [100.0, 50.0] * 15
    treated = [90.0, 60.0] * 15
    result = ve.paired_comparison(base, treated, seed=1)
    assert ve.verdict(result, ve.mae(base)) == ve.VERDICT_INCONCLUSIVE


def test_ket_luan_trung_thuc_ca_khi_sai_so_tang():
    base = [100.0 + i for i in range(30)]
    result = ve.paired_comparison(base, [v + 30.0 for v in base], seed=1)
    assert ve.verdict(result, ve.mae(base)) == ve.VERDICT_WORSE


def test_giam_duoi_nguong_khong_goi_la_ro_ret():
    base = [100.0 + i for i in range(30)]
    result = ve.paired_comparison(base, [v - 2.0 for v in base], seed=1)
    assert ve.verdict(result, ve.mae(base)) == ve.VERDICT_SMALL


def test_cung_mot_dia_chup_nhieu_anh_nam_cung_fold():
    plates = [_plate(f"{i}.jpg", plate_id="dia-1" if i < 3 else f"p{i}") for i in range(12)]
    folds = ve.make_folds(plates, k=3, seed=42)
    assert len({folds[f"{i}.jpg"] for i in range(3)}) == 1


def test_kho_vi_du_khong_chua_dia_trong_fold_dang_do_va_long_nhau():
    plates = [_plate(f"{i}.jpg") for i in range(20)]
    folds = ve.make_folds(plates, k=4, seed=42)
    small = ve.pool_for(plates, folds, fold=0, level=5, seed=42)
    large = ve.pool_for(plates, folds, fold=0, level=10, seed=42)
    assert all(folds[p.image_file] != 0 for p in large)
    assert [p.image_file for p in large[:5]] == [p.image_file for p in small]


def test_muc_learning_curve_khong_vuot_kho_va_luon_co_muc_day():
    plates = [_plate(f"{i}.jpg") for i in range(20)]
    folds = ve.make_folds(plates, k=4, seed=42)
    assert ve.effective_levels([0, 10, 25, 50, 100], plates, folds) == [0, 10, 15]


class FakeEngine:
    """Gemini giả: lượt đầu đoán 150 g, có ví dụ thì về 190 g, lượt 2 không ví dụ giữ nguyên."""
    def __init__(self):
        self.refine_calls = 0

    def analyze(self, plate):
        return {"food_name": plate.dish_name, "calories_kcal": 999.0, "components": [
            {"name": "Món thử nghiệm", "grams": 150, "kcal_per_100g": 100, "protein_per_100g": 2, "carb_per_100g": 20,
             "fat_per_100g": 1}]}

    def refine(self, plate, analysis, examples, repeat):
        self.refine_calls += 1
        return [{"name": "Món thử nghiệm", "grams": 190 if examples != "[]" else 150}]

    def retrieve(self, name, pool):
        return ([p.image_file for p in pool[:3]], "ví dụ:" + ",".join(p.image_file for p in pool[:3])) if pool else ([], "[]")


def test_thuc_nghiem_giu_nguyen_luot_dau_va_do_duoc_tac_dung_cua_vi_du():
    plates = [_plate(f"{i}.jpg", grams=200.0) for i in range(20)]
    engine = FakeEngine()
    result = ve.run_experiment(plates, engine, levels=[0, 5, 15], folds=4, repeats=2, seed=42)
    curve = {row["level"]: row for row in result["curve"]}
    assert curve[0]["grams"]["mae"] == 50.0 and curve[0]["coverage"] == 0
    assert curve[15]["grams"]["mae"] == 10.0 and curve[15]["coverage"] == 20
    assert result["control"]["grams"]["mae"] == 50.0
    assert result["primary"]["vs_first"]["verdict"] == ve.VERDICT_CLEAR
    assert result["primary"]["vs_control"]["verdict"] == ve.VERDICT_CLEAR


def test_luot_tinh_chinh_sai_cau_truc_quay_ve_ket_qua_dau_va_duoc_dem():
    class Broken(FakeEngine):
        def refine(self, plate, analysis, examples, repeat):
            return [{"name": "Món khác", "grams": 190}]
    plates = [_plate(f"{i}.jpg", grams=200.0) for i in range(20)]
    result = ve.run_experiment(plates, Broken(), levels=[0, 15], folds=4, repeats=1, seed=42)
    assert result["curve"][-1]["grams"]["mae"] == 50.0
    assert result["invalid_refines"] > 0


def test_anh_bi_tu_choi_duoc_bao_cao_khong_am_tham_bo_qua():
    class Rejecting(FakeEngine):
        def analyze(self, plate):
            return {"food_name": None, "components": []} if plate.image_file == "0.jpg" else super().analyze(plate)
    plates = [_plate(f"{i}.jpg", grams=200.0) for i in range(20)]
    result = ve.run_experiment(plates, Rejecting(), levels=[0], folds=4, repeats=1, seed=42)
    assert result["excluded"] == ["0.jpg"] and result["curve"][0]["n"] == 19


def test_bao_cao_chay_thu_co_canh_bao_khong_dung_so_lieu():
    plates = [_plate(f"{i}.jpg", grams=200.0) for i in range(20)]
    result = ve.run_experiment(plates, FakeEngine(), levels=[0, 15], folds=4, repeats=1, seed=42)
    draft = ve.render_report(result, official=False, meta={"model": "giả"})
    final = ve.render_report(result, official=True, meta={"model": "giả"})
    assert ve.DRY_RUN_BANNER in draft and ve.DRY_RUN_BANNER not in final
    assert "—" not in final and "–" not in final


def test_bieu_do_learning_curve_la_svg_hop_le():
    plates = [_plate(f"{i}.jpg", grams=200.0) for i in range(20)]
    result = ve.run_experiment(plates, FakeEngine(), levels=[0, 5, 15], folds=4, repeats=1, seed=42)
    svg = ve.render_curve_svg(result, metric="grams")
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>") and "<polyline" in svg
