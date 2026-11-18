"""Đo MAE khẩu phần và learning curve few-shot trên bộ ảnh cân thật.

Chạy từ backend/:
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/vision_eval.py check
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/vision_eval.py mae
    PYTHONUTF8=1 ./.venv/Scripts/python.exe scripts/vision_eval.py curve --levels 0,5,10,20

Dữ liệu chưa đạt điều kiện thì script dừng. --allow-unverified chỉ để kiểm tra kỹ thuật: kết quả bị đóng
dấu CHẠY THỬ và ghi ra file *_DRYRUN. Kết quả gọi Gemini được lưu lại nên chạy lại không tốn thêm lượt gọi.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import FewShotExample  # noqa: E402
from app.services import few_shot, gemini_vision, vision_eval as ve  # noqa: E402

DATASET = BACKEND / "eval" / "vision_dataset"
RESULTS = BACKEND / "eval" / "results"
RETRIES = (5, 20, 60)
EXAMPLE_NS = uuid.UUID("6f1c5d3e-52a4-4b0e-9b64-0d6a1f3c7e21")


class GeminiEngine:
    """Gọi đúng các hàm của hệ thống thật, ghim một model và lưu mọi phản hồi để chạy lại được."""

    def __init__(self, image_dir: Path, store: Path, model: str, pause: float):
        self.image_dir, self.store, self.model, self.pause = image_dir, store, model, pause
        gemini_vision.GEMINI_VISION_MODELS = (model,)
        few_shot._embed = lambda value: None  # thực nghiệm chỉ dùng nhánh trigram để kết quả lặp lại được
        self.cache = {}
        if store.exists():
            for line in store.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                self.cache[row["key"]] = row["output"]

    def _key(self, kind: str, plate: ve.Plate, *parts) -> str:
        image = hashlib.sha256((self.image_dir / plate.image_file).read_bytes()).hexdigest()
        prompt = gemini_vision.FOOD_ANALYSIS_PROMPT if kind == "analyze" else gemini_vision.REFINE_PROMPT
        raw = json.dumps([kind, image, self.model, hashlib.sha256(prompt.encode()).hexdigest(), *parts], ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _cached(self, key: str, label: str, call):
        if key in self.cache:
            return self.cache[key]
        for wait in (*RETRIES, None):
            try:
                output = call()
                break
            except Exception as e:  # noqa: BLE001
                if wait is None:
                    raise RuntimeError(f"Gemini lỗi ở {label}. Chạy lại lệnh để tiếp tục từ chỗ dừng.") from e
                print(f"  {label}: lỗi {type(e).__name__}, thử lại sau {wait} giây", flush=True)
                time.sleep(wait)
        self.cache[key] = output
        self.store.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store, "a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "label": label, "output": output}, ensure_ascii=False) + "\n")
        print(f"  xong {label}", flush=True)
        time.sleep(self.pause)
        return output

    def _image(self, plate: ve.Plate) -> tuple[bytes, str]:
        path = self.image_dir / plate.image_file
        return path.read_bytes(), mimetypes.guess_type(path.name)[0] or "image/jpeg"

    def analyze(self, plate: ve.Plate) -> dict:
        return self._cached(self._key("analyze", plate), f"lượt đầu {plate.image_file}",
                            lambda: gemini_vision.analyze_food_image(*self._image(plate)))

    def refine(self, plate: ve.Plate, analysis: dict, examples: str, repeat: int):
        def call():
            image, mime = self._image(plate)
            return gemini_vision.refine_components(image, mime, analysis, examples)
        return self._cached(self._key("refine", plate, examples, repeat), f"lượt 2 {plate.image_file} #{repeat}", call)

    def retrieve(self, name: str | None, pool: list[ve.Plate]) -> tuple[list[str], str]:
        """Dùng đúng câu truy vấn thật trên kho tạm trong transaction; luôn rollback nên DB không đổi."""
        if not pool:
            return [], "[]"
        owners = {uuid.uuid5(EXAMPLE_NS, p.image_file): p.image_file for p in pool}
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with SessionLocal() as db:
            try:
                db.execute(text("UPDATE few_shot_examples SET is_active = FALSE WHERE is_active"))
                for index, plate in enumerate(pool):
                    db.add(FewShotExample(
                        id=uuid.uuid5(EXAMPLE_NS, plate.image_file),
                        food_name=few_shot.clean_name(self.analyze(plate)["food_name"]),
                        components=few_shot.example_components([{"name": c.name, "grams": c.grams} for c in plate.components]),
                        total_kcal=sum(c.grams * (c.kcal_per_100g or 0) / 100 for c in plate.components),
                        is_active=True, created_at=start + timedelta(seconds=index),
                    ))
                db.flush()
                found = few_shot.retrieve(db, name)
                return [owners[e.id] for e in found], few_shot.prompt_examples(found)
            finally:
                db.rollback()


def _name_coverage(plates: list[ve.Plate]) -> tuple[int, str | None]:
    """Số đĩa có món tương tự ở đĩa khác, theo đúng ngưỡng trigram của hệ thống."""
    sql = text("SELECT similarity(f_unaccent(lower(:a)), f_unaccent(lower(:b)))")
    try:
        with SessionLocal() as db:
            covered = sum(any(p.plate_id != q.plate_id and
                              db.execute(sql, {"a": p.dish_name, "b": q.dish_name}).scalar() >= few_shot.MIN_NAME_SIMILARITY
                              for q in plates) for p in plates)
        return covered, None
    except Exception as e:  # noqa: BLE001
        return 0, f"Không đo được độ phủ tên món vì chưa kết nối được Postgres: {type(e).__name__}"


def _print_audit(audit: dict, plates: list[ve.Plate]) -> None:
    print(f"Số đĩa: {audit['plates']} | đã cân thật: {audit['weighed']} | đủ dữ liệu kcal: {audit['kcal_ready']}")
    covered, problem = _name_coverage(plates)
    if problem:
        print("[CẢNH BÁO]", problem)
    else:
        print(f"Đĩa có món tương tự ở đĩa khác: {covered}/{len(plates)}")
        if covered < ve.MIN_COVERAGE_WARNING * len(plates):
            print("[CẢNH BÁO] Độ phủ thấp: few-shot chỉ chạy khi có món tương tự, nên cần chụp lặp lại mỗi món ở nhiều đĩa.")
    for item in audit["warnings"]:
        print("[CẢNH BÁO]", item)
    for item in audit["blocking"]:
        print("[CHẶN]", item)
    print("Kết luận:", "ĐỦ ĐIỀU KIỆN đo chính thức." if not audit["blocking"] else "CHƯA ĐỦ ĐIỀU KIỆN đo chính thức.")


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BACKEND, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "không rõ"


def _run(args, plates: list[ve.Plate], audit: dict) -> int:
    if audit["blocking"] and not args.allow_unverified:
        print("\nDừng: dữ liệu chưa đạt điều kiện, không gọi Gemini.")
        return 2
    selected = plates[:args.limit] if args.limit else plates
    official = not audit["blocking"] and not args.allow_unverified and not args.limit
    suffix = "" if official else "_DRYRUN"
    out = Path(args.out)
    engine = GeminiEngine(Path(args.images), out / f"vision_eval_runs{suffix}.jsonl", args.model, args.pause)
    levels = [int(v) for v in args.levels.split(",")] if args.command == "curve" else None
    if levels is not None:
        with SessionLocal() as db:
            db.execute(text("SELECT 1 FROM few_shot_examples LIMIT 1"))
    result = ve.run_experiment(selected, engine, levels, folds=args.folds, repeats=args.repeats, seed=args.seed)
    meta = {"Thời điểm chạy": f"{datetime.now():%Y-%m-%d %H:%M}", "Model": args.model, "Commit": _commit(),
            "Truy hồi ví dụ": f"trigram theo tên món, ngưỡng {few_shot.MIN_NAME_SIMILARITY}, tối đa {few_shot.TOP_K} ví dụ"}
    out.mkdir(parents=True, exist_ok=True)
    report = out / f"vision_eval_report{suffix}.md"
    report.write_text(ve.render_report(result, official, meta), encoding="utf-8")
    (out / f"vision_eval_plates{suffix}.json").write_text(
        json.dumps(result["per_plate"], ensure_ascii=False, indent=2), encoding="utf-8")
    if levels is not None:
        (out / f"vision_eval_curve{suffix}.csv").write_text(ve.curve_csv(result), encoding="utf-8")
        for metric in ("kcal", "grams"):
            (out / f"vision_eval_curve_{metric}{suffix}.svg").write_text(ve.render_curve_svg(result, metric), encoding="utf-8")
    print(f"\nĐã ghi báo cáo: {report}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("check", "mae", "curve"))
    parser.add_argument("--ground-truth", default=str(DATASET / "ground_truth.csv"))
    parser.add_argument("--images", default=str(DATASET / "images"))
    parser.add_argument("--out", default=str(RESULTS))
    parser.add_argument("--levels", default="0,5,10,20", help="Số ca trong kho, luôn có thêm mức đầy kho")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3, help="Số lần lặp lượt 2 cho mỗi đĩa")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default=gemini_vision.GEMINI_VISION_MODELS[0])
    parser.add_argument("--pause", type=float, default=1.0, help="Số giây nghỉ giữa hai lượt gọi")
    parser.add_argument("--limit", type=int, help="Chỉ chạy N đĩa đầu, kết quả luôn là chạy thử")
    parser.add_argument("--allow-unverified", action="store_true", help="Kiểm tra kỹ thuật, kết quả luôn là chạy thử")
    args = parser.parse_args()

    plates = ve.load_ground_truth(args.ground_truth)
    audit = ve.audit_dataset(plates, args.images)
    _print_audit(audit, plates)
    if args.command == "check":
        return 1 if audit["blocking"] else 0
    return _run(args, plates, audit)


if __name__ == "__main__":
    raise SystemExit(main())
