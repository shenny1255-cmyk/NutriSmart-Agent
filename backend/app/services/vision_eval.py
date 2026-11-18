"""Đo sai số ước lượng khẩu phần và learning curve của kho few-shot (kế hoạch ĐATN v2, mục 2.1 và 2.3).

Nguyên tắc chống tự lừa:
- Chỉ đĩa được cân thật (gt_source=WEIGHED, có người cân và ngày cân) mới cho ra số liệu chính thức.
- Đĩa đang đo không bao giờ nằm trong kho ví dụ của chính nó (chia fold theo plate_id).
- Mọi điều kiện dùng chung một kết quả lượt đầu, nên so sánh được theo cặp trên từng đĩa.
- Có nhóm đối chứng "lượt 2 không có ví dụ" để tách tác dụng của ví dụ khỏi tác dụng của việc nhìn lại.
- Kết luận do quy tắc cố định quyết định, kể cả khi sai số không giảm hoặc tăng lên.

Script chạy và ghi báo cáo: scripts/vision_eval.py. Quy trình: docs/thuc_nghiem_vision_hitl.md
"""
from __future__ import annotations

import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from app.services import portion
from app.services.guardrails import _norm

MIN_PLATES = 30
RESAMPLES = 5000
NAME_MATCH_THRESHOLD = 0.6
# Chốt trước khi chạy: giảm ít nhất 10% MAE mới được gọi là giảm rõ rệt.
MIN_CLEAR_REDUCTION = 0.10
MIN_COVERAGE_WARNING = 0.5

VERDICT_CLEAR = "GIẢM RÕ RỆT"
VERDICT_SMALL = "GIẢM NHƯNG DƯỚI NGƯỠNG 10%"
VERDICT_INCONCLUSIVE = "CHƯA ĐỦ BẰNG CHỨNG"
VERDICT_WORSE = "SAI SỐ TĂNG"

DRY_RUN_BANNER = ("> **CHẠY THỬ KỸ THUẬT - KHÔNG DÙNG SỐ LIỆU NÀY TRONG BÁO CÁO.** "
                  "Dữ liệu chưa đạt điều kiện cân thật hoặc mới chạy một phần bộ ảnh.")


@dataclass(frozen=True)
class ActualComponent:
    name: str
    grams: float
    kcal_per_100g: float | None


@dataclass(frozen=True)
class Plate:
    image_file: str
    plate_id: str
    dish_name: str
    weighed: bool
    components: list[ActualComponent]


def _density(row: dict, name: str) -> float | None:
    """kcal/100 g: ưu tiên số nhóm ghi trong file, sau đó tra bảng. Không có thì để trống, không đoán."""
    raw = (row.get("kcal_per_100g") or "").strip()
    if raw:
        value = float(raw)
        if not 0 <= value <= 900:
            raise ValueError(f"kcal_per_100g không hợp lệ ở {row['image_file']}: {raw}")
        return value
    match = portion.match_component(name)
    return match["per_100g"]["energy_kcal"] if match else None


def _is_weighed(row: dict) -> bool:
    return ((row.get("gt_source") or "").strip().upper() == "WEIGHED"
            and bool((row.get("weighed_by") or "").strip()) and bool((row.get("weighed_at") or "").strip()))


def load_ground_truth(path: Path | str) -> list[Plate]:
    groups: dict[str, list[dict]] = defaultdict(list)
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            groups[row["image_file"].strip()].append(row)
    plates = []
    for image, rows in groups.items():
        components = []
        for row in rows:
            name = row["component_name"].strip()
            try:
                grams = float(row["actual_grams"])
            except (TypeError, ValueError):
                raise ValueError(f"actual_grams không phải số ở {image}: {name}") from None
            if not 0 < grams <= portion.MAX_GRAMS:
                raise ValueError(f"actual_grams ngoài khoảng cho phép ở {image}: {name}")
            components.append(ActualComponent(name, grams, _density(row, name)))
        plates.append(Plate(image_file=image, plate_id=(rows[0].get("plate_id") or "").strip() or image,
                            dish_name=rows[0]["dish_name"].strip(), weighed=all(_is_weighed(r) for r in rows),
                            components=components))
    return plates


def audit_dataset(plates: list[Plate], image_dir: Path | str) -> dict:
    """Điều kiện để số liệu được coi là chính thức. `blocking` khác rỗng thì không được công bố."""
    image_dir = Path(image_dir)
    weighed = [p for p in plates if p.weighed]
    blocking, warnings = [], []
    if len(weighed) < len(plates):
        blocking.append(f"{len(plates) - len(weighed)}/{len(plates)} đĩa chưa có số cân thật "
                        "(cần gt_source=WEIGHED, weighed_by, weighed_at ở mọi dòng).")
    if len(weighed) < MIN_PLATES:
        blocking.append(f"Mới có {len(weighed)} đĩa đã cân, tối thiểu {MIN_PLATES} đĩa.")
    missing = [p.image_file for p in plates if not (image_dir / p.image_file).is_file()]
    if missing:
        blocking.append("Thiếu file ảnh: " + ", ".join(missing))
    no_kcal = [p.image_file for p in plates if any(c.kcal_per_100g is None for c in p.components)]
    if no_kcal:
        warnings.append(f"{len(no_kcal)} đĩa thiếu kcal/100 g ở ít nhất một thành phần nên không tính được MAE kcal: "
                        + ", ".join(no_kcal))
    return {"plates": len(plates), "weighed": len(weighed), "kcal_ready": len(plates) - len(no_kcal),
            "blocking": blocking, "warnings": warnings}


def plate_error(plate: Plate, predicted: list[dict]) -> dict:
    """Sai số trên tổng đĩa. Đây là chỉ số chính vì không phụ thuộc cách ghép tên thành phần."""
    grams_actual = sum(c.grams for c in plate.components)
    grams_pred = sum(c["grams"] for c in predicted)
    out = {"grams_actual": grams_actual, "grams_signed": grams_pred - grams_actual,
           "grams_abs": abs(grams_pred - grams_actual), "kcal_actual": None, "kcal_signed": None, "kcal_abs": None}
    if all(c.kcal_per_100g is not None for c in plate.components):
        kcal_actual = sum(c.grams * c.kcal_per_100g / 100 for c in plate.components)
        kcal_pred = sum(c["grams"] * c["per_100g"]["energy_kcal"] / 100 for c in predicted)
        out.update(kcal_actual=kcal_actual, kcal_signed=kcal_pred - kcal_actual, kcal_abs=abs(kcal_pred - kcal_actual))
    return out


def _name_similarity(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    tokens_a, tokens_b = set(a.split()), set(b.split())
    if tokens_a and tokens_b and (tokens_a <= tokens_b or tokens_b <= tokens_a):
        return 0.9
    return SequenceMatcher(None, a, b).ratio()


def component_errors(actual: list[ActualComponent], predicted: list[dict]) -> dict:
    """Ghép tên gần giống. Thành phần bỏ sót hoặc thêm thừa vẫn tính vào sai số, không bị loại khỏi mẫu."""
    pairs = sorted(((_name_similarity(a.name, p["name"]), i, j) for i, a in enumerate(actual)
                    for j, p in enumerate(predicted)), key=lambda x: (-x[0], x[1], x[2]))
    used_a, used_p, errors = set(), set(), []
    for score, i, j in pairs:
        if score >= NAME_MATCH_THRESHOLD and i not in used_a and j not in used_p:
            used_a.add(i)
            used_p.add(j)
            errors.append(abs(actual[i].grams - predicted[j]["grams"]))
    errors += [a.grams for i, a in enumerate(actual) if i not in used_a]
    errors += [p["grams"] for j, p in enumerate(predicted) if j not in used_p]
    return {"matched": len(used_a), "missed": len(actual) - len(used_a), "extra": len(predicted) - len(used_p),
            "abs_errors": errors}


def mae(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def wape(abs_errors: list[float], actuals: list[float]) -> float:
    """Sai số tương đối theo tổng, không bị đĩa rất nhỏ làm méo như MAPE."""
    total = sum(actuals)
    return sum(abs_errors) / total if total else 0.0


def _percentile(ordered: list[float], q: float) -> float:
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def bootstrap_ci(values: list[float], seed: int = 42) -> tuple[float, float]:
    """Khoảng tin cậy 95% của trung bình bằng bootstrap phân vị."""
    if not values:
        return 0.0, 0.0
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(RESAMPLES))
    return _percentile(means, 0.025), _percentile(means, 0.975)


def paired_comparison(baseline: list[float], treated: list[float], seed: int = 42) -> dict:
    """So sánh theo cặp trên cùng đĩa: bootstrap cho hiệu trung bình, hoán vị dấu cho p hai phía."""
    diffs = [t - b for b, t in zip(baseline, treated, strict=True)]
    observed = abs(mae(diffs))
    rng = random.Random(seed)
    extreme = sum(abs(sum(d if rng.random() < 0.5 else -d for d in diffs)) / len(diffs) >= observed - 1e-12
                  for _ in range(RESAMPLES)) if diffs else RESAMPLES
    return {"n": len(diffs), "mean_diff": mae(diffs), "ci": bootstrap_ci(diffs, seed),
            "p_value": (extreme + 1) / (RESAMPLES + 1), "improved": sum(d < -1e-9 for d in diffs),
            "worse": sum(d > 1e-9 for d in diffs), "tied": sum(abs(d) <= 1e-9 for d in diffs)}


def verdict(comparison: dict, baseline_mae: float) -> str:
    low, high = comparison["ci"]
    if low > 0:
        return VERDICT_WORSE
    if high >= 0:
        return VERDICT_INCONCLUSIVE
    reduction = -comparison["mean_diff"] / baseline_mae if baseline_mae else 0.0
    return VERDICT_CLEAR if reduction >= MIN_CLEAR_REDUCTION else VERDICT_SMALL


def make_folds(plates: list[Plate], k: int, seed: int) -> dict[str, int]:
    """Chia theo plate_id; xếp theo tên món trước khi chia để cùng một món trải đều qua các fold."""
    groups: dict[str, list[Plate]] = defaultdict(list)
    for plate in plates:
        groups[plate.plate_id].append(plate)
    if len(groups) < k:
        raise ValueError(f"Cần ít nhất {k} đĩa khác nhau để chia {k} fold")
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    keys.sort(key=lambda key: _norm(groups[key][0].dish_name))
    return {p.image_file: index % k for index, key in enumerate(keys) for p in groups[key]}


def pool_for(plates: list[Plate], folds: dict[str, int], fold: int, level: int, seed: int) -> list[Plate]:
    """Kho ví dụ lồng nhau: kho nhỏ luôn là phần đầu của kho lớn, nên đường cong chỉ đổi theo số ca."""
    pool = sorted((p for p in plates if folds[p.image_file] != fold), key=lambda p: p.image_file)
    random.Random(seed + fold).shuffle(pool)
    return pool[:level]


def effective_levels(levels: list[int], plates: list[Plate], folds: dict[str, int]) -> list[int]:
    largest = min(sum(1 for p in plates if folds[p.image_file] != fold) for fold in set(folds.values()))
    return sorted({level for level in levels if level <= largest} | {0, largest})


def _mean_error(errors: list[dict]) -> dict:
    out = {}
    for key in errors[0]:
        values = [e[key] for e in errors]
        out[key] = None if any(v is None for v in values) else mae(values)
    return out


def _summary(errors: list[dict], metric: str, seed: int) -> dict:
    rows = [e for e in errors if e[f"{metric}_abs"] is not None]
    values = [e[f"{metric}_abs"] for e in rows]
    return {"n": len(rows), "mae": mae(values), "ci": bootstrap_ci(values, seed),
            "wape": wape(values, [e[f"{metric}_actual"] for e in rows]),
            "bias": mae([e[f"{metric}_signed"] for e in rows])}


def _compare(base: list[dict], treated: list[dict], metric: str, seed: int) -> dict:
    pairs = [(b[f"{metric}_abs"], t[f"{metric}_abs"]) for b, t in zip(base, treated, strict=True)
             if b[f"{metric}_abs"] is not None]
    baseline = [b for b, _ in pairs]
    result = paired_comparison(baseline, [t for _, t in pairs], seed)
    reduction = -result["mean_diff"] / mae(baseline) if mae(baseline) else 0.0
    return {**result, "baseline_mae": mae(baseline), "reduction": reduction, "verdict": verdict(result, mae(baseline))}


def _score_refined(plate: Plate, analysis: dict, first: list[dict], outputs: list, counter: dict) -> dict:
    """Lượt tinh chỉnh sai cấu trúc thì quay về kết quả đầu, giống hệt hành vi của hệ thống thật."""
    errors = []
    for refined in outputs:
        merged = portion.merge_refined_grams(analysis["components"], refined)
        components = portion.build_components(merged) if merged is not None else []
        if not components:
            counter["invalid"] += 1
            components = first
        errors.append(plate_error(plate, components))
    return _mean_error(errors)


def run_experiment(plates: list[Plate], engine, levels: list[int] | None, folds: int = 5, repeats: int = 3,
                   seed: int = 42) -> dict:
    """levels=None chỉ đo lượt đầu (MAE). `engine` cung cấp analyze, refine, retrieve."""
    analyses, firsts, excluded = {}, {}, []
    for plate in plates:
        analysis = engine.analyze(plate)
        components = portion.build_components(analysis.get("components"))
        if components:
            analyses[plate.image_file], firsts[plate.image_file] = analysis, components
        else:
            excluded.append(plate.image_file)
    valid = [p for p in plates if p.image_file in analyses]
    first_errors = [plate_error(p, firsts[p.image_file]) for p in valid]

    comp = [component_errors(p.components, firsts[p.image_file]) for p in valid]
    comp_values = [v for c in comp for v in c["abs_errors"]]
    legacy = [abs(float(analyses[p.image_file]["calories_kcal"]) - e["kcal_actual"])
              for p, e in zip(valid, first_errors, strict=True)
              if e["kcal_actual"] is not None and analyses[p.image_file].get("calories_kcal") is not None]
    result = {
        "n_plates": len(valid), "excluded": excluded, "folds": folds, "repeats": repeats, "seed": seed,
        "components": {"mae": mae(comp_values), "ci": bootstrap_ci(comp_values, seed), "n": len(comp_values),
                       "matched": sum(c["matched"] for c in comp), "missed": sum(c["missed"] for c in comp),
                       "extra": sum(c["extra"] for c in comp)},
        "legacy_kcal": {"n": len(legacy), "mae": mae(legacy), "ci": bootstrap_ci(legacy, seed)},
        "control": None, "primary": None, "invalid_refines": 0,
        "per_plate": {p.image_file: {"first": e} for p, e in zip(valid, first_errors, strict=True)},
    }
    level_zero = {"level": 0, "n": len(valid), "coverage": 0, "mean_examples": 0.0,
                  "grams": _summary(first_errors, "grams", seed), "kcal": _summary(first_errors, "kcal", seed)}
    result["curve"] = [level_zero]
    if levels is None:
        return result

    fold_of = make_folds(valid, folds, seed)
    counter = {"invalid": 0}
    control_errors = []
    for plate in valid:
        analysis = analyses[plate.image_file]
        outputs = [engine.refine(plate, analysis, "[]", r) for r in range(repeats)]
        error = _score_refined(plate, analysis, firsts[plate.image_file], outputs, counter)
        control_errors.append(error)
        result["per_plate"][plate.image_file]["control"] = error
    result["control"] = {"grams": _summary(control_errors, "grams", seed), "kcal": _summary(control_errors, "kcal", seed)}

    final_errors = first_errors
    for level in [lv for lv in effective_levels(levels, valid, fold_of) if lv > 0]:
        errors, used = [], []
        for plate in valid:
            pool = pool_for(valid, fold_of, fold_of[plate.image_file], level, seed)
            analysis = analyses[plate.image_file]
            found, block = engine.retrieve(analysis.get("food_name"), pool)
            used.append(len(found))
            if found:
                outputs = [engine.refine(plate, analysis, block, r) for r in range(repeats)]
                error = _score_refined(plate, analysis, firsts[plate.image_file], outputs, counter)
            else:
                error = plate_error(plate, firsts[plate.image_file])
            errors.append(error)
            result["per_plate"][plate.image_file][f"level_{level}"] = {**error, "examples": found}
        result["curve"].append({
            "level": level, "n": len(valid), "coverage": sum(1 for u in used if u), "mean_examples": mae(used),
            "grams": {**_summary(errors, "grams", seed), "vs_first": _compare(first_errors, errors, "grams", seed)},
            "kcal": {**_summary(errors, "kcal", seed), "vs_first": _compare(first_errors, errors, "kcal", seed)},
        })
        final_errors = errors

    metric = "kcal" if level_zero["kcal"]["n"] else "grams"
    result["primary"] = {"metric": metric, "level": result["curve"][-1]["level"],
                         "vs_first": _compare(first_errors, final_errors, metric, seed),
                         "vs_control": _compare(control_errors, final_errors, metric, seed)}
    result["invalid_refines"] = counter["invalid"]
    return result


UNITS = {"grams": "g", "kcal": "kcal"}
LABELS = {"grams": "Tổng khối lượng đĩa", "kcal": "Tổng năng lượng đĩa"}


def _fmt(value: float | None, digits: int = 1) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _ci(pair: tuple[float, float]) -> str:
    return f"{pair[0]:.1f} đến {pair[1]:.1f}"


def _p(value: float) -> str:
    return "< 0.001" if value < 0.001 else f"{value:.3f}"


def _mae_table(result: dict) -> list[str]:
    lines = ["| Chỉ số | n | MAE | KTC 95% | WAPE | Sai lệch trung bình (dự đoán - thực tế) |", "|---|---|---|---|---|---|"]
    first = result["curve"][0]
    for metric in ("grams", "kcal"):
        s = first[metric]
        lines.append(f"| {LABELS[metric]} ({UNITS[metric]}) | {s['n']} | {_fmt(s['mae'])} | {_ci(s['ci'])} "
                     f"| {s['wape']:.1%} | {s['bias']:+.1f} |")
    c = result["components"]
    lines.append(f"| Từng thành phần (g) | {c['n']} | {_fmt(c['mae'])} | {_ci(c['ci'])} | - | - |")
    old = result["legacy_kcal"]
    lines.append(f"| Kcal tổng do AI tự đoán, cách cũ (kcal) | {old['n']} | {_fmt(old['mae'])} | {_ci(old['ci'])} | - | - |")
    return lines


def _curve_table(result: dict, metric: str) -> list[str]:
    unit = UNITS[metric]
    lines = [f"| Số ca trong kho | Đĩa có ví dụ khớp | MAE ({unit}) | KTC 95% | WAPE | Thay đổi so với 0 ca | p |",
             "|---|---|---|---|---|---|---|"]
    for row in result["curve"]:
        s = row[metric]
        cmp = s.get("vs_first")
        change = f"{-cmp['reduction']:+.1%}" if cmp else "mốc so sánh"
        lines.append(f"| {row['level']} | {row['coverage']}/{row['n']} | {_fmt(s['mae'])} | {_ci(s['ci'])} "
                     f"| {s['wape']:.1%} | {change} | {_p(cmp['p_value']) if cmp else '-'} |")
    return lines


def _comparison_row(name: str, cmp: dict, unit: str) -> str:
    return (f"| {name} | {cmp['n']} | {cmp['mean_diff']:+.1f} {unit} | {_ci(cmp['ci'])} | {-cmp['reduction']:+.1%} "
            f"| {cmp['improved']}/{cmp['worse']}/{cmp['tied']} | {_p(cmp['p_value'])} | **{cmp['verdict']}** |")


def render_report(result: dict, official: bool, meta: dict) -> str:
    lines = ["# Kết quả đo sai số khẩu phần và learning curve few-shot", ""]
    if not official:
        lines += [DRY_RUN_BANNER, ""]
    lines += [f"- {key}: {value}" for key, value in meta.items()]
    lines += [f"- Số đĩa đưa vào đo: {result['n_plates']}; số fold: {result['folds']}; số lần lặp lượt 2: "
              f"{result['repeats']}; seed: {result['seed']}"]
    if result["excluded"]:
        lines.append(f"- Đĩa bị AI từ chối hoặc không tách được thành phần (đã loại): {', '.join(result['excluded'])}")
    lines += ["", "## 1. Sai số của lượt nhận diện đầu (chưa có few-shot)", ""] + _mae_table(result) + [""]
    if result["primary"] is None:
        return "\n".join(lines) + "\n"
    primary = result["primary"]
    unit = UNITS[primary["metric"]]
    lines += ["## 2. Learning curve theo số ca trong kho", "", "### Theo kcal", ""] + _curve_table(result, "kcal")
    lines += ["", "### Theo gram", ""] + _curve_table(result, "grams")
    control = result["control"]
    lines += ["", "### Đối chứng: lượt 2 không có ví dụ", "",
              f"- MAE kcal: {_fmt(control['kcal']['mae'])} (KTC 95%: {_ci(control['kcal']['ci'])})",
              f"- MAE gram: {_fmt(control['grams']['mae'])} (KTC 95%: {_ci(control['grams']['ci'])})",
              f"- Lượt tinh chỉnh sai cấu trúc, đã quay về kết quả đầu: {result['invalid_refines']}",
              "", f"## 3. Kiểm định giả thuyết chính (kho {primary['level']} ca, theo {unit})", "",
              "| So sánh | n | Hiệu MAE | KTC 95% của hiệu | Thay đổi | Đĩa tốt hơn/kém hơn/bằng | p | Kết luận |",
              "|---|---|---|---|---|---|---|---|",
              _comparison_row("Few-shot so với lượt đầu", primary["vs_first"], unit),
              _comparison_row("Few-shot so với lượt 2 không ví dụ", primary["vs_control"], unit), ""]
    supported = primary["vs_first"]["verdict"] == primary["vs_control"]["verdict"] == VERDICT_CLEAR
    lines.append("**Giả thuyết HITL " + ("được dữ liệu ủng hộ." if supported else "chưa được dữ liệu ủng hộ.") + "** "
                 "Điều kiện: cả hai so sánh đều có KTC 95% nằm hoàn toàn dưới 0 và MAE giảm ít nhất 10%.")
    return "\n".join(lines) + "\n"


def curve_csv(result: dict) -> str:
    rows = ["level,coverage,n,mae_kcal,kcal_ci_low,kcal_ci_high,mae_grams,grams_ci_low,grams_ci_high"]
    for r in result["curve"]:
        k, g = r["kcal"], r["grams"]
        rows.append(f"{r['level']},{r['coverage']},{r['n']},{k['mae']:.2f},{k['ci'][0]:.2f},{k['ci'][1]:.2f},"
                    f"{g['mae']:.2f},{g['ci'][0]:.2f},{g['ci'][1]:.2f}")
    return "\n".join(rows) + "\n"


def render_curve_svg(result: dict, metric: str = "kcal") -> str:
    """Biểu đồ đường có dải KTC 95%, nền trắng để chèn thẳng vào báo cáo."""
    width, height, left, right, top, bottom = 760, 440, 80, 30, 50, 70
    curve = result["curve"]
    control = (result.get("control") or {}).get(metric)
    peak = max([r[metric]["ci"][1] for r in curve] + ([control["mae"]] if control else [])) or 1.0
    span = max(r["level"] for r in curve) or 1
    x = lambda v: left + v / span * (width - left - right)
    y = lambda v: height - bottom - v / (peak * 1.1) * (height - top - bottom)
    points = " ".join(f"{x(r['level']):.1f},{y(r[metric]['mae']):.1f}" for r in curve)
    band = [f"{x(r['level']):.1f},{y(r[metric]['ci'][1]):.1f}" for r in curve]
    band += [f"{x(r['level']):.1f},{y(r[metric]['ci'][0]):.1f}" for r in reversed(curve)]
    font = 'font-family="Arial, sans-serif" fill="#1f2933"'
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
             f'<text x="{width / 2}" y="28" text-anchor="middle" font-size="17" font-weight="700" {font}>'
             f'MAE {UNITS[metric]} theo số ca trong kho few-shot</text>']
    for step in range(6):
        value = peak * 1.1 * step / 5
        parts.append(f'<line x1="{left}" x2="{width - right}" y1="{y(value):.1f}" y2="{y(value):.1f}" stroke="#e4e7eb"/>')
        parts.append(f'<text x="{left - 10}" y="{y(value) + 4:.1f}" text-anchor="end" font-size="12" {font}>{value:.0f}</text>')
    parts.append(f'<polygon points="{" ".join(band)}" fill="#0f766e" fill-opacity="0.15"/>')
    if control:
        parts.append(f'<line x1="{left}" x2="{width - right}" y1="{y(control["mae"]):.1f}" y2="{y(control["mae"]):.1f}" '
                     'stroke="#b45309" stroke-width="2" stroke-dasharray="7 5"/>')
        parts.append(f'<text x="{width - right}" y="{y(control["mae"]) - 8:.1f}" text-anchor="end" font-size="12" '
                     f'{font}>Đối chứng: lượt 2 không ví dụ</text>')
    parts.append(f'<polyline points="{points}" fill="none" stroke="#0f766e" stroke-width="2.5"/>')
    for r in curve:
        parts.append(f'<circle cx="{x(r["level"]):.1f}" cy="{y(r[metric]["mae"]):.1f}" r="4.5" fill="#0f766e"/>')
        parts.append(f'<text x="{x(r["level"]):.1f}" y="{height - bottom + 22}" text-anchor="middle" font-size="12" '
                     f'{font}>{r["level"]}</text>')
    parts.append(f'<text x="{(left + width - right) / 2}" y="{height - 18}" text-anchor="middle" font-size="13" {font}>'
                 'Số ca đã duyệt trong kho</text>')
    parts.append(f'<text transform="translate(22 {(top + height - bottom) / 2}) rotate(-90)" text-anchor="middle" '
                 f'font-size="13" {font}>MAE ({UNITS[metric]}), dải màu là KTC 95%</text>')
    return "\n".join(parts + ["</svg>"]) + "\n"
