"""Định lượng khẩu phần từ ảnh (kế hoạch ĐATN v2, mục 2.3 - GĐ3).

Nguyên tắc: AI chỉ ước lượng GRAM từng thành phần; kcal/macro tra từ Bảng thành phần thực phẩm
Việt Nam 2007. Thành phần chưa ánh xạ chắc chắn được thì giữ nhãn AI_ESTIMATE để người dùng thấy
rõ nguồn số liệu, không ghép bừa vào dòng có tên gần giống.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.services import food_composition
from app.services.guardrails import _norm

MAP_PATH = Path(__file__).resolve().parents[2] / "data" / "component_fct_map.json"
NUTRIENTS = ("energy_kcal", "protein_g", "carb_g", "fat_g")
MAX_COMPONENTS = 15
MAX_GRAMS = 3000.0
GRAM_TOLERANCE = 0.5


def _per_100g(row: dict, factor: float = 1.0) -> dict:
    return {k: round(float(row.get(k) or 0.0) * factor, 2) for k in NUTRIENTS}


@lru_cache(maxsize=1)
def _lookup() -> tuple[dict, dict]:
    """→ (mã → dòng bảng, tên/alias chuẩn hóa → (dòng bảng, hệ số nấu chín))."""
    rows = food_composition.load_csv()
    by_code = {r["code"]: r for r in rows}
    by_name = {_norm(r["name_vi"]): r for r in rows}
    index = {name: (row, 1.0) for name, row in by_name.items()}
    for item in json.loads(MAP_PATH.read_text(encoding="utf-8"))["items"]:
        row = by_name[_norm(item["fct_name"])]
        for alias in item["aliases"]:
            index[_norm(alias)] = (row, float(item.get("cooked_factor", 1.0)))
    return by_code, index


def match_component(name: str) -> dict | None:
    hit = _lookup()[1].get(_norm(name))
    if hit is None:
        return None
    row, factor = hit
    return {"fct_code": row["code"], "fct_name": row["name_vi"], "per_100g": _per_100g(row, factor)}


def _valid_grams(value) -> float | None:
    try:
        grams = float(value)
    except (TypeError, ValueError):
        return None
    return round(grams, 1) if 0 < grams <= MAX_GRAMS else None


def _ai_per_100g(raw: dict) -> dict | None:
    """Giá trị AI ước tính/100 g, chỉ nhận khi nằm trong giới hạn vật lý."""
    try:
        values = {
            "energy_kcal": float(raw["kcal_per_100g"]),
            "protein_g": float(raw["protein_per_100g"]),
            "carb_g": float(raw["carb_per_100g"]),
            "fat_g": float(raw["fat_per_100g"]),
        }
    except (KeyError, TypeError, ValueError):
        return None
    macros_ok = all(0 <= values[k] <= 100 for k in ("protein_g", "carb_g", "fat_g"))
    return values if macros_ok and 0 <= values["energy_kcal"] <= 900 else None


def build_components(raw_items) -> list[dict]:
    """Chuẩn hóa thành phần AI trả về. Một mục không dùng được → trả [] để không tính thiếu calo."""
    if not isinstance(raw_items, list) or not 0 < len(raw_items) <= MAX_COMPONENTS:
        return []
    out = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            return []
        name = str(raw.get("name") or "").strip()
        grams = _valid_grams(raw.get("grams"))
        if not name or grams is None:
            return []
        match = match_component(name)
        if match is None:
            per_100g = _ai_per_100g(raw)
            if per_100g is None:
                return []
            match = {"fct_code": None, "fct_name": None, "per_100g": per_100g}
        out.append({"name": name, "grams": grams, "ai_grams": grams,
                    "source": "FCT" if match["fct_code"] else "AI_ESTIMATE", **match})
    return out


def totals(components: list[dict]) -> dict:
    return {k: round(sum(c["per_100g"][k] * c["grams"] / 100 for c in components), 1) for k in NUTRIENTS}


def enrich(analysis: dict) -> dict:
    """Thay tổng do AI tự đoán bằng tổng tính từ gram; vẫn giữ số AI để so sánh trước/sau."""
    result = dict(analysis)
    components = build_components(result.pop("components", None))
    result["components"] = components
    result["ai_total_kcal"] = result.get("calories_kcal")
    if components:
        sums = totals(components)
        result.update(calories_kcal=sums["energy_kcal"], protein_g=sums["protein_g"],
                      carb_g=sums["carb_g"], fat_g=sums["fat_g"])
    return result


def recalculate(final_items: list[dict], predicted: list[dict]) -> list[dict]:
    """Tính lại phía server từ gram người dùng chốt; không tin số kcal do client gửi lên."""
    known = {(c["name"], c.get("fct_code")): c for c in predicted}
    by_code = _lookup()[0]
    out = []
    for item in final_items:
        name, code = item["name"].strip(), item.get("fct_code")
        base = known.get((name, code))
        if base is not None:
            out.append({**base, "grams": float(item["grams"])})
        elif code in by_code:
            row = by_code[code]
            out.append({"name": name, "grams": float(item["grams"]), "ai_grams": 0.0, "source": "FCT",
                        "fct_code": code, "fct_name": row["name_vi"], "per_100g": _per_100g(row)})
        else:
            raise ValueError(f"Thành phần không hợp lệ: {name}")
    return out


def was_corrected(predicted: list[dict], final: list[dict]) -> bool:
    before = {(c["name"], c.get("fct_code")): c["grams"] for c in predicted}
    after = {(c["name"], c.get("fct_code")): c["grams"] for c in final}
    return before.keys() != after.keys() or any(abs(before[k] - after[k]) > GRAM_TOLERANCE for k in before)
