"""Warning Engine — lớp guardrail rule-based chạy SAU khi AI trả kết quả (kế hoạch ĐATN v2, mục 2.5).

Nguyên tắc:
- Deterministic, không nhờ LLM tự kiểm tra chính nó.
- Áp dụng cho cả 3 đầu ra AI: thực đơn sinh ra, kết quả quét ảnh, câu trả lời chat.
- Dị ứng ưu tiên recall hơn precision: nghi ngờ thì cảnh báo.
- Mỗi rule bệnh lý ghi nguồn tham khảo.

> Ứng dụng chỉ hỗ trợ, không thay thế chẩn đoán/tư vấn y khoa. Tình trạng kiểm chứng
> từng nguồn (đã xác minh số quyết định / còn cần đọc bản gốc): eval/sources.md

Mỗi cảnh báo là dict: {level, code, message, source, context}
- level: DANGER (đỏ) | WARNING (vàng) | INFO (xanh)
- code:  ALLERGEN | CONDITION | KCAL_LOW | KCAL_HIGH | TARGET_LOW | LOW_CONFIDENCE | NO_GROUNDING
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

LEVEL_ORDER = ["DANGER", "WARNING", "INFO"]

# ---------- Ngưỡng ----------

# Mức calo tối thiểu/ngày theo giới tính: chế độ giảm cân của Guideline AHA/ACC/TOS 2013 về
# quản lý thừa cân, béo phì kê 1.200–1.500 kcal (nữ) và 1.500–1.800 kcal (nam) → lấy cận dưới.
# Không rõ giới tính → mốc thấp hơn để không báo động giả.
MIN_KCAL_BY_GENDER = {"FEMALE": 1200, "MALE": 1500}
MIN_KCAL_DEFAULT = 1200

# Vượt quá 120% chỉ tiêu ngày → cảnh báo vàng.
KCAL_HIGH_RATIO = 1.2

# Vùng tin cậy của Vision. Đây chỉ là GIẢ THUYẾT BAN ĐẦU (mục 2.4.2): confidence do LLM
# tự báo cáo, chưa hiệu chỉnh — cần chọn lại từ reliability diagram trên bộ ảnh cân thật.
CONF_HIGH = 0.7   # ≥ ngưỡng này: tự điền, người dùng chỉ bấm lưu
CONF_LOW = 0.3    # < ngưỡng này: yêu cầu chụp lại; ở giữa: yêu cầu xác nhận khẩu phần

DISCLAIMER = "NutriSmart chỉ hỗ trợ tham khảo, không thay thế chẩn đoán hay tư vấn của bác sĩ."


def min_kcal_for(gender: str | None) -> int:
    return MIN_KCAL_BY_GENDER.get((gender or "").upper(), MIN_KCAL_DEFAULT)


# ---------- Hồ sơ dùng để kiểm tra ----------

@dataclass(frozen=True)
class GuardProfile:
    gender: str | None = None
    allergens: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    daily_kcal_target: int | None = None


def profile_from_user(user) -> GuardProfile:
    """Gom dị ứng/bệnh nền từ danh mục chuẩn + ô tự khai báo."""
    info = getattr(user, "profile", None)
    if info is None:
        return GuardProfile()
    conditions = [c.name for c in (getattr(info, "conditions", None) or [])]
    conditions += [str(x) for x in (getattr(info, "custom_conditions", None) or [])]
    allergens = [a.name for a in (getattr(info, "allergens", None) or [])]
    allergens += [
        (item.get("name", "") if isinstance(item, dict) else str(item))
        for item in (getattr(info, "custom_allergens", None) or [])
    ]
    return GuardProfile(
        gender=getattr(info, "gender", None),
        allergens=tuple(a for a in allergens if a and a.strip()),
        conditions=tuple(c for c in conditions if c and c.strip()),
        daily_kcal_target=getattr(info, "daily_calorie_target", None),
    )


# ---------- So khớp văn bản tiếng Việt ----------

def _norm(s: str | None) -> str:
    """Chữ thường + NFC + gộp khoảng trắng. GIỮ dấu: bỏ dấu thì "cá" trùng "cà"."""
    s = unicodedata.normalize("NFC", s or "").lower()
    return re.sub(r"\s+", " ", s).strip()


@lru_cache(maxsize=2048)
def _word_re(phrase: str) -> re.Pattern:
    # \w trong Python đã hiểu chữ có dấu tiếng Việt → ranh giới từ đúng cho "cá" vs "cách"
    return re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)")


def _first_match(text: str, keywords: tuple[str, ...], negatives: tuple[str, ...] = ()) -> str | None:
    """Từ khóa đầu tiên xuất hiện trong text sau khi đã xóa các cụm loại trừ."""
    t = _norm(text)
    if not t:
        return None
    for neg in negatives:
        t = _word_re(neg).sub(" | ", t)
    # Ưu tiên cụm dài ("mắm tôm" trước "tôm") để thông điệp cụ thể hơn
    for kw in sorted(keywords, key=len, reverse=True):
        if _word_re(kw).search(t):
            return kw
    return None


# ---------- Từ điển dị nguyên: món → nguyên liệu → nhóm dị nguyên ----------

@dataclass(frozen=True)
class _Group:
    aliases: tuple[str, ...]      # tên người dùng có thể chọn/gõ cho nhóm này
    keywords: tuple[str, ...]     # nguyên liệu, món, gia vị chứa dị nguyên (kể cả dị ứng ẩn)
    negatives: tuple[str, ...] = ()  # cụm trông giống nhưng không chứa dị nguyên


ALLERGEN_GROUPS: dict[str, _Group] = {
    "shellfish": _Group(
        aliases=("hải sản có vỏ", "hải sản", "giáp xác", "nhuyễn thể", "động vật có vỏ"),
        keywords=("tôm", "tép", "cua", "ghẹ", "riêu", "tôm hùm", "ốc", "sò", "sò điệp", "điệp",
                  "nghêu", "ngao", "hến", "hàu", "trai", "mực", "bạch tuộc", "bề bề",
                  "mắm tôm", "mắm ruốc", "ruốc", "tôm khô", "dầu hào", "hải sản"),
        negatives=("ruốc thịt", "ruốc gà", "ruốc heo", "ruốc bò", "chà bông"),
    ),
    "fish": _Group(
        aliases=("cá",),
        keywords=("cá", "nước mắm", "mắm nêm", "mắm cá", "mắm sặc", "mắm linh", "chả cá",
                  "mắm", "dầu cá"),
        negatives=("cá nhân", "cá thể", "cá tính", "cá cược", "mắm tôm", "mắm ruốc"),
    ),
    "peanut": _Group(
        aliases=("đậu phộng", "lạc"),
        keywords=("đậu phộng", "lạc rang", "kẹo lạc", "xôi lạc", "muối lạc", "bơ đậu phộng",
                  "gỏi cuốn", "bò bía", "nộm"),
    ),
    "milk": _Group(
        aliases=("sữa bò", "sữa", "lactose", "đạm sữa"),
        keywords=("sữa", "sữa bò", "sữa tươi", "sữa chua", "sữa đặc", "phô mai", "pho mát",
                  "váng sữa", "bơ lạt", "bơ bò", "kem", "whey", "bánh flan"),
        negatives=("sữa đậu nành", "sữa hạt", "sữa gạo", "sữa dừa", "sữa ong chúa",
                   "sữa yến mạch", "sữa hạnh nhân", "sữa óc chó", "sữa rửa mặt"),
    ),
    "gluten": _Group(
        aliases=("gluten", "lúa mì", "bột mì"),
        keywords=("lúa mì", "bột mì", "bánh mì", "mì", "mì gói", "mì tôm", "mì ý", "mì ống",
                  "nui", "bánh bao", "bánh quy", "bánh ngọt", "bánh kem", "bia", "lúa mạch",
                  "xì dầu", "pasta", "spaghetti", "sandwich"),
        negatives=("mì quảng", "mì chính", "bún", "phở", "miến"),
    ),
    "egg": _Group(
        aliases=("trứng",),
        keywords=("trứng", "ốp la", "mayonnaise", "mayonaise", "sốt mayo", "bánh flan",
                  "bông lan", "chả trứng"),
    ),
    "soy": _Group(
        aliases=("đậu nành", "đậu tương"),
        keywords=("đậu nành", "đậu tương", "đậu phụ", "đậu hũ", "tàu hũ", "tào phớ",
                  "sữa đậu nành", "nước tương", "xì dầu", "tương đen", "tương bần", "tương hột",
                  "chao", "miso", "tempeh", "edamame"),
    ),
    "tree_nut": _Group(
        aliases=("hạt cây", "các loại hạt"),
        keywords=("hạnh nhân", "óc chó", "hạt điều", "hạt dẻ", "hồ đào", "mắc ca", "macca",
                  "hạt phỉ", "dẻ cười", "sữa hạt"),
    ),
    "sesame": _Group(
        aliases=("hạt mè", "mè", "vừng"),
        keywords=("mè", "vừng", "dầu mè", "dầu vừng", "muối vừng", "muối mè", "bánh đa"),
    ),
    "chicken": _Group(
        aliases=("thịt gà", "gà"),
        keywords=("gà", "thịt gà", "nước dùng gà", "ruốc gà"),
        negatives=("trứng gà",),
    ),
    "beef": _Group(
        aliases=("thịt bò", "bò"),
        keywords=("bò", "thịt bò", "bò viên", "nước dùng bò"),
        negatives=("bò bía", "sữa bò", "bơ bò", "bò sữa"),
    ),
}

# Dị nguyên không qua đường ăn uống → Warning Engine thực phẩm bỏ qua.
NON_FOOD_ALLERGENS = {"latex", "bụi nhà", "phấn hoa", "lông động vật", "penicillin", "aspirin",
                      "mạt bụi", "nấm mốc"}


@lru_cache(maxsize=512)
def _resolve_allergen(name: str) -> _Group | None:
    """Tên dị nguyên người dùng khai báo → nhóm trong từ điển (hoặc nhóm nguyên văn)."""
    n = _norm(name)
    if not n or n in NON_FOOD_ALLERGENS:
        return None
    for group in ALLERGEN_GROUPS.values():
        if n in group.aliases:
            return group
    for group in ALLERGEN_GROUPS.values():
        if n in group.keywords:      # gõ "tôm" → hiểu là cả nhóm giáp xác
            return group
    return _Group(aliases=(n,), keywords=(n,))


# ---------- Bệnh nền: bảng chống chỉ định ----------

@dataclass(frozen=True)
class _ConditionRule:
    aliases: tuple[str, ...]   # cụm có trong tên bệnh người dùng khai báo
    advice: str
    keywords: tuple[str, ...]
    source: str
    negatives: tuple[str, ...] = ()


CONDITION_RULES: dict[str, _ConditionRule] = {
    "gout": _ConditionRule(
        aliases=("gout", "gút"),
        advice="người bệnh gout nên hạn chế thực phẩm giàu purin (nội tạng, hải sản, bia rượu)",
        keywords=("nội tạng", "lòng heo", "lòng lợn", "lòng bò", "lòng gà", "gan", "cật",
                  "bầu dục", "dồi", "tiết canh", "óc heo", "cá cơm", "cá mòi", "cá trích",
                  "tôm", "cua", "ghẹ", "mực", "sò", "hàu", "nghêu", "ốc", "hải sản",
                  "bia", "rượu"),
        negatives=("gan nhiễm mỡ", "men gan", "bệnh gan", "xơ gan", "chức năng gan"),
        source="Bộ Y tế — QĐ 361/QĐ-BYT (25/01/2014), Hướng dẫn chẩn đoán và điều trị các bệnh cơ xương khớp",
    ),
    "diabetes": _ConditionRule(
        aliases=("đái tháo đường", "tiểu đường"),
        advice="người đái tháo đường típ 2 nên hạn chế đường đơn và thực phẩm có chỉ số đường huyết cao",
        keywords=("đường", "chè", "nước ngọt", "trà sữa", "bánh ngọt", "bánh kem", "kẹo", "mứt",
                  "nước mía", "mật ong", "siro", "sữa đặc", "xôi", "kem", "bánh flan",
                  "nước ép"),
        negatives=("không đường", "ít đường", "đường huyết", "chè xanh", "nước chè"),
        source="Bộ Y tế — QĐ 5481/QĐ-BYT (30/12/2020), Hướng dẫn chẩn đoán và điều trị đái tháo đường típ 2",
    ),
    "hypertension": _ConditionRule(
        aliases=("tăng huyết áp", "cao huyết áp", "huyết áp cao"),
        advice="người tăng huyết áp nên giảm muối/natri (dưới 5 g muối mỗi ngày)",
        keywords=("dưa muối", "cà muối", "dưa cải muối", "cá khô", "mực khô", "khô bò",
                  "khô gà", "tôm khô", "xúc xích", "lạp xưởng", "thịt nguội", "giăm bông",
                  "mì gói", "mì tôm", "đồ hộp", "mắm tôm", "mắm nêm", "mắm ruốc", "ruốc",
                  "snack", "muối ớt"),
        source="Bộ Y tế — QĐ 3192/QĐ-BYT (31/08/2010), Hướng dẫn chẩn đoán và điều trị tăng huyết áp; WHO Fact sheet Salt reduction: < 5 g muối/ngày",
    ),
    "dyslipidemia": _ConditionRule(
        aliases=("rối loạn lipid", "mỡ máu", "cholesterol"),
        advice="người rối loạn lipid máu nên hạn chế chất béo bão hòa, đồ chiên rán và nội tạng",
        keywords=("chiên", "rán", "quay", "mỡ", "da gà", "ba chỉ", "nội tạng", "lòng heo",
                  "lòng lợn", "óc heo", "xúc xích", "lạp xưởng", "bơ thực vật", "gà rán",
                  "khoai tây chiên"),
        negatives=("mỡ hành",),
        source="Hội Tim mạch học Quốc gia Việt Nam — Khuyến cáo về chẩn đoán và điều trị rối loạn lipid máu (2015)",
    ),
    "fatty_liver": _ConditionRule(
        aliases=("gan nhiễm mỡ",),
        advice="người gan nhiễm mỡ nên tránh rượu bia, hạn chế đồ ngọt và đồ chiên rán",
        keywords=("bia", "rượu", "nước ngọt", "trà sữa", "chiên", "rán", "bánh ngọt",
                  "gà rán", "khoai tây chiên"),
        source="Viện Dinh dưỡng Quốc gia — Khuyến nghị chế độ ăn cho người gan nhiễm mỡ",
    ),
    "ckd": _ConditionRule(
        aliases=("thận mạn", "suy thận", "bệnh thận"),
        advice="người bệnh thận mạn cần kiểm soát kali, phospho, natri và lượng đạm",
        keywords=("chuối", "khoai tây", "khoai lang", "nước cam", "cam", "nước dừa",
                  "nội tạng", "dưa muối", "cà muối", "đồ hộp", "xúc xích", "mì gói",
                  "sữa", "phô mai", "đậu đỏ", "đậu đen"),
        negatives=("sữa đậu nành",),
        source="Bộ Y tế — QĐ 2388/QĐ-BYT (12/08/2024), Hướng dẫn chẩn đoán và điều trị bệnh thận mạn và một số bệnh lý thận",
    ),
}


@lru_cache(maxsize=512)
def _resolve_condition(name: str) -> _ConditionRule | None:
    n = _norm(name)
    # Duyệt "gan nhiễm mỡ" trước "mỡ máu"... không trùng; thứ tự dict là đủ
    for rule in CONDITION_RULES.values():
        if any(alias in n for alias in rule.aliases):
            return rule
    return None


# ---------- Tạo cảnh báo ----------

def _w(level: str, code: str, message: str, source: str | None = None,
       context: str | None = None) -> dict:
    return {"level": level, "code": code, "message": message, "source": source, "context": context}


def _sorted(warnings: list[dict]) -> list[dict]:
    return sorted(warnings, key=lambda w: LEVEL_ORDER.index(w["level"]))


def _allergen_warnings(text: str, profile: GuardProfile, level: str, subject: str) -> list[dict]:
    out = []
    for name in profile.allergens:
        group = _resolve_allergen(name)
        if group is None:
            continue
        kw = _first_match(text, group.keywords, group.negatives)
        if kw:
            out.append(_w(level, "ALLERGEN",
                          f"{subject} có “{kw}” — bạn khai báo dị ứng {name.strip()}."))
    return out


def check_food_text(text: str, profile: GuardProfile) -> list[dict]:
    """Kiểm tra tên/mô tả một món theo dị ứng (đỏ) và bệnh nền (vàng)."""
    out = _allergen_warnings(text, profile, "DANGER", "Món")
    for name in profile.conditions:
        rule = _resolve_condition(name)
        if rule is None:
            continue
        kw = _first_match(text, rule.keywords, rule.negatives)
        if kw:
            out.append(_w("WARNING", "CONDITION",
                          f"Món có “{kw}” — {rule.advice} (bệnh nền: {name.strip()}).",
                          source=rule.source))
    return _sorted(out)


def check_day_kcal(total_kcal: float, profile: GuardProfile, context: str | None = None) -> list[dict]:
    """Tổng calo một ngày: dưới mức tối thiểu → đỏ; vượt 120% chỉ tiêu → vàng."""
    minimum = min_kcal_for(profile.gender)
    if total_kcal < minimum:
        return [_w("DANGER", "KCAL_LOW",
                   f"Tổng {total_kcal:.0f} kcal/ngày thấp hơn mức tối thiểu an toàn {minimum} kcal.",
                   context=context)]
    target = profile.daily_kcal_target
    if target and total_kcal > target * KCAL_HIGH_RATIO:
        pct = round(total_kcal / target * 100)
        return [_w("WARNING", "KCAL_HIGH",
                   f"Tổng {total_kcal:.0f} kcal vượt {pct}% chỉ tiêu ngày ({target} kcal).",
                   context=context)]
    return []


def _day_ranges(days: list[int]) -> str:
    """[1,2,3,5] → "1–3, 5"."""
    days = sorted(set(days))
    parts, start = [], days[0]
    for prev, cur in zip(days, days[1:] + [None]):
        if cur != prev + 1 if cur is not None else True:
            parts.append(f"{start}–{prev}" if prev > start else f"{start}")
            start = cur
    return ", ".join(parts)


def compact_contexts(locations: list[tuple[int, str | None]]) -> str:
    """[(ngày, bữa), …] → "Trưa, Tối · ngày 1–7" — gom bữa có cùng tập ngày."""
    by_meal: dict[str | None, list[int]] = {}
    for day, meal in locations:
        by_meal.setdefault(meal, []).append(day)
    groups: dict[str, list[str]] = {}   # chuỗi ngày → các bữa, giữ thứ tự xuất hiện
    for meal, days in by_meal.items():
        groups.setdefault(_day_ranges(days), []).append(meal or "")
    out = []
    for days, meals in groups.items():
        names = ", ".join(m for m in meals if m)
        out.append(f"{names} · ngày {days}" if names else f"ngày {days}")
    return "; ".join(out)


def _merge(warnings: list[dict]) -> list[dict]:
    """Gom cảnh báo trùng (cùng code + thông điệp) và rút gọn vị trí xuất hiện."""
    merged: dict[tuple[str, str], dict] = {}
    locs: dict[tuple[str, str], list] = {}
    for w in warnings:
        key = (w["code"], w["message"])
        loc = w.pop("_loc", None)
        merged.setdefault(key, w)
        if loc:
            locs.setdefault(key, []).append(loc)
    for key, w in merged.items():
        if key in locs:
            w["context"] = compact_contexts(locs[key])
    return list(merged.values())


def check_plan(content: dict | None, profile: GuardProfile) -> list[dict]:
    """Kiểm tra toàn bộ thực đơn 7 ngày do AI sinh ra."""
    out: list[dict] = []
    target = profile.daily_kcal_target
    minimum = min_kcal_for(profile.gender)
    if target and target < minimum:
        out.append(_w("DANGER", "TARGET_LOW",
                      f"Chỉ tiêu {target} kcal/ngày thấp hơn mức tối thiểu an toàn {minimum} kcal."))

    days = (content or {}).get("days") if isinstance(content, dict) else None
    for i, day in enumerate(days or [], start=1):
        meals = (day or {}).get("meals") or []
        total = 0.0
        for meal in meals:
            if not isinstance(meal, dict):
                continue
            for w in check_food_text(str(meal.get("name") or ""), profile):
                out.append({**w, "_loc": (i, meal.get("type") or "Bữa")})
            try:
                total += float(meal.get("kcal") or 0)
            except (TypeError, ValueError):
                pass
        if total > 0:
            out.extend({**w, "_loc": (i, None)} for w in check_day_kcal(total, profile))
    return _sorted(_merge(out))


def check_meal_scan(analysis: dict, profile: GuardProfile, consumed_today: float = 0.0) -> list[dict]:
    """Kiểm tra kết quả quét ảnh: độ tin cậy, dị ứng/bệnh nền, vượt chỉ tiêu ngày."""
    if not analysis or not analysis.get("is_food_image"):
        return []
    out: list[dict] = []

    conf = float(analysis.get("confidence") or 0.0)
    if conf < CONF_LOW:
        out.append(_w("DANGER", "LOW_CONFIDENCE",
                      f"AI không chắc chắn về món này (độ tin cậy {conf:.0%}). Hãy chụp lại rõ hơn."))
    elif conf < CONF_HIGH:
        out.append(_w("WARNING", "LOW_CONFIDENCE",
                      f"Độ tin cậy {conf:.0%} — hãy kiểm tra lại tên món và khẩu phần trước khi lưu."))

    text = " . ".join(str(analysis.get(k) or "") for k in ("food_name", "description"))
    out.extend(check_food_text(text, profile))

    kcal = float(analysis.get("calories_kcal") or 0.0)
    target = profile.daily_kcal_target
    if target and kcal > 0 and consumed_today + kcal > target * KCAL_HIGH_RATIO:
        total = consumed_today + kcal
        out.append(_w("WARNING", "KCAL_HIGH",
                      f"Thêm món này, hôm nay bạn sẽ nạp {total:.0f} kcal — "
                      f"vượt {round(total / target * 100)}% chỉ tiêu {target} kcal."))
    return _sorted(out)


def check_chat_reply(reply: str, profile: GuardProfile, citation_count: int) -> list[dict]:
    """Câu trả lời chat: nhắc tới dị nguyên (vàng — có thể chỉ là lời dặn tránh) và
    thiếu trích dẫn tài liệu đã duyệt (xanh — nhắc người dùng kiểm chứng)."""
    out = _allergen_warnings(reply, profile, "WARNING", "Câu trả lời nhắc tới")
    for w in out:
        w["message"] += " Hãy kiểm tra kỹ trước khi áp dụng."
    if citation_count == 0:
        out.append(_w("INFO", "NO_GROUNDING",
                      "Câu trả lời không dựa trên tài liệu đã được chuyên gia duyệt — "
                      "hãy tham khảo thêm ý kiến chuyên môn."))
    return _sorted(out)
