from datetime import date
import re
from typing import Annotated, Literal
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict, BeforeValidator, AfterValidator


def _normalize_email(v: str) -> str:
    """Trim + thường hoá email trước khi EmailStr kiểm tra → không phân biệt hoa/thường."""
    return v.strip().lower() if isinstance(v, str) else v


# Chấp nhận MỌI nhà cung cấp (EmailStr không chặn theo domain), luôn lưu ở dạng chuẩn hoá.
NormalizedEmail = Annotated[EmailStr, BeforeValidator(_normalize_email)]


def _validate_birth_date(value: date) -> date:
    """Ngày sinh phải ở trong khoảng tuổi hợp lý từ 0 đến 120."""
    today = date.today()
    if value > today:
        raise ValueError("Ngày sinh không được ở trong tương lai")
    age = today.year - value.year - (
        (today.month, today.day) < (value.month, value.day)
    )
    if age > 120:
        raise ValueError("Tuổi không được vượt quá 120")
    return value


BirthDate = Annotated[date, AfterValidator(_validate_birth_date)]


def _validate_full_name(value: str) -> str:
    """Chuẩn hóa và chỉ chấp nhận tên người gồm chữ cùng dấu phân cách thông dụng."""
    normalized = " ".join(value.strip().split())
    if not 2 <= len(normalized) <= 100:
        raise ValueError("Họ và tên phải có từ 2 đến 100 ký tự")
    parts = re.split(r"[ '\-’]", normalized)
    if any(not part or not all(char.isalpha() for char in part) for part in parts):
        raise ValueError("Họ và tên chỉ được chứa chữ cái, khoảng trắng, dấu nháy hoặc gạch nối")
    return normalized


FullName = Annotated[str, AfterValidator(_validate_full_name)]


def _validate_food_name(value: str) -> str:
    """Tên món phải dễ đọc nhưng vẫn cho phép số và dấu thường gặp trong thực phẩm."""
    normalized = " ".join(value.strip().split())
    if not 2 <= len(normalized) <= 100:
        raise ValueError("Tên món phải có từ 2 đến 100 ký tự")
    if sum(char.isalpha() for char in normalized) < 2:
        raise ValueError("Tên món phải có ít nhất 2 chữ cái")
    allowed_punctuation = " &/().,'’+-%"
    if any(not (char.isalpha() or char.isdigit() or char in allowed_punctuation) for char in normalized):
        raise ValueError("Tên món chứa ký tự không hợp lệ")
    return normalized


FoodName = Annotated[str, AfterValidator(_validate_food_name)]


# ---------- Register ----------
class ProfileIn(BaseModel):
    gender: Literal["MALE", "FEMALE", "OTHER"]
    birth_date: BirthDate
    height_cm: float = Field(gt=50, lt=250)
    weight_kg: float = Field(ge=20, le=300)
    activity_level: int = Field(ge=1, le=5)
    goal: Literal["LOSE_WEIGHT", "MAINTAIN", "GAIN_MUSCLE", "MEDICAL"]
    condition_ids: list[int] = []
    allergen_ids: list[int] = []


class RegisterIn(BaseModel):
    email: NormalizedEmail
    password: str = Field(min_length=8)
    full_name: FullName
    profile: ProfileIn


class LoginIn(BaseModel):
    email: NormalizedEmail
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Catalog ----------
class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class StaffPermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    can_manage_users: bool = False
    can_manage_foods: bool = False
    can_manage_categories: bool = False
    can_review_documents: bool = False
    can_review_plans: bool = False
    can_review_ai_chat: bool = False
    can_review_logs: bool = False
    can_manage_permissions: bool = False


class StaffProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    staff_code: str
    full_name: str
    gender: str | None = None
    birth_date: date | None = None
    specialization: str | None = None
    qualification: str | None = None
    employment_status: str = "ACTIVE"
    permissions: StaffPermissionOut | None = None


# ---------- User ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    full_name: str | None = None
    role: str
    staff_profile: StaffProfileOut | None = None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    gender: str | None = None
    birth_date: date | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    bmi: float | None = None
    activity_level: int | None = None
    goal: str | None = None
    daily_calorie_target: int | None = None
    conditions: list[ItemOut] = []
    allergens: list[ItemOut] = []


class MeOut(UserOut):
    """GET /auth/me trả về kèm hồ sơ sức khỏe để frontend dùng."""
    profile: ProfileOut | None = None


class UserProfileUpdateIn(BaseModel):
    """Cập nhật thông tin cá nhân + hồ sơ sức khỏe."""
    full_name: FullName | None = None
    # Hồ sơ sức khỏe
    gender: Literal["MALE", "FEMALE", "OTHER"] | None = None
    birth_date: BirthDate | None = None
    height_cm: float | None = Field(default=None, gt=50, lt=250)
    weight_kg: float | None = Field(default=None, ge=20, le=300)
    activity_level: int | None = Field(default=None, ge=1, le=5)
    goal: Literal["LOSE_WEIGHT", "MAINTAIN", "GAIN_MUSCLE", "MEDICAL"] | None = None
    condition_ids: list[int] | None = None
    allergen_ids: list[int] | None = None


# ---------- Check-in tiến độ 14 ngày ----------
class CheckinSubmitIn(BaseModel):
    actual_weight_kg: float = Field(ge=20, le=300, allow_inf_nan=False)
    actual_waist_cm: float | None = Field(default=None, ge=30, le=250, allow_inf_nan=False)
    actual_activity_level: int = Field(ge=1, le=5)
    adherence_pct: int = Field(ge=0, le=100)
    energy_level: int = Field(ge=1, le=5)
    hunger_level: int = Field(ge=1, le=5)
    sleep_quality: int = Field(ge=1, le=5)
    notes: str | None = Field(default=None, max_length=1000)


class CheckinDecisionIn(BaseModel):
    action: Literal["CONTINUE", "APPLY_ADJUSTMENT"]


class PlanCheckinOut(BaseModel):
    id: UUID
    plan_id: UUID
    period_number: int
    start_date: date
    period_end: date
    due_date: date
    grace_until: date
    display_status: str
    status: str
    baseline_weight_kg: float
    expected_weight_min_kg: float
    expected_weight_max_kg: float
    target_kcal_snapshot: int
    goal_snapshot: str
    actual_weight_kg: float | None = None
    actual_waist_cm: float | None = None
    actual_activity_level: int | None = None
    adherence_pct: int | None = None
    energy_level: int | None = None
    hunger_level: int | None = None
    sleep_quality: int | None = None
    notes: str | None = None
    meal_log_days: int | None = None
    avg_kcal_intake: float | None = None
    weight_change_kg: float | None = None
    data_quality_result: str | None = None
    adherence_result: str | None = None
    outcome_result: str | None = None
    safety_flags: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    recommendation_reason: str | None = None
    proposed_kcal_target: int | None = None
    ai_feedback: str | None = None
    feedback_status: str
    decision: str | None = None
    adjusted_plan_id: UUID | None = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    title: str
    body: str | None = None
    is_read: bool
    created_at: datetime


# ---------- Tracking ----------
class DailySummaryOut(BaseModel):
    day: date
    kcal_intake: float
    kcal_burned: float
    daily_calorie_target: int | None
    kcal_remaining: float | None


class ActivityIn(BaseModel):
    steps: int = Field(ge=0, default=0)
    calories_burned: float = Field(ge=0, default=0.0)
    distance_km: float = Field(ge=0, default=0.0)
    log_date: date | None = None  # None = hôm nay


class TodayActivityOut(BaseModel):
    steps: int
    calories_burned: float
    distance_km: float
    log_date: date


# ---------- Nhật ký thủ công (bữa ăn / vận động / cân nặng) ----------
class FoodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    serving_desc: str | None = None
    calories_kcal: float
    protein_g: float | None = None
    carb_g: float | None = None
    fat_g: float | None = None


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    met_value: float | None = None
    category: str | None = None


class ManualMealIn(BaseModel):
    """Ghi bữa ăn tay: chọn món có sẵn (food_id) hoặc gõ tên món mới."""
    food_id: UUID | None = None
    food_name: FoodName | None = None
    calories_kcal: float | None = Field(default=None, ge=1, le=5000)
    protein_g: float = Field(default=0.0, ge=0)
    carb_g: float = Field(default=0.0, ge=0)
    fat_g: float = Field(default=0.0, ge=0)
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER", "SNACK"] = "LUNCH"
    quantity: float = Field(default=1.0, ge=0.5, le=20)
    log_date: date | None = None


class MealLogOut(BaseModel):
    id: int
    food_name: str
    meal_type: str
    quantity: float
    calories_kcal: float
    log_date: date


class ManualActivityIn(BaseModel):
    """Ghi buổi tập tay. Bỏ trống calories_burned → tự tính theo MET × cân nặng × phút."""
    exercise_id: int
    duration_min: int = Field(ge=1, le=600)
    calories_burned: float | None = Field(default=None, ge=0)
    steps: int = Field(default=0, ge=0)
    started_at: datetime | None = None
    ended_at: datetime | None = None


class ActivityLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exercise_name: str
    duration_min: int
    calories_burned: float
    steps: int
    started_at: datetime | None = None
    ended_at: datetime | None = None
    logged_at: datetime


class WeightIn(BaseModel):
    weight_kg: float = Field(ge=20, le=300)
    recorded_at: date | None = None


class WeightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    recorded_at: date
    weight_kg: float
    bmi: float | None = None


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    # Đây là schema TRẢ VỀ: email đã được validate lúc đăng ký, không validate lại.
    # Dùng EmailStr ở đây thì chỉ cần MỘT bản ghi cũ/rác có domain lạ (vd .local)
    # là cả danh sách người dùng hỏng → HTTP 500.
    email: str
    full_name: str | None
    role: str
    updated_at: datetime


class UpdateRoleIn(BaseModel):
    role: Literal["ADMIN", "EXPERT", "USER"]


# ---------- Danh mục (tài liệu / thuốc) ----------
class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    parent_id: int | None = None      # chỉ dùng cho danh mục tài liệu


class DocCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    parent_id: int | None = None
    so_tai_lieu: int = 0


# ---------- Documents ----------
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    source_url: str | None
    source_name: str | None
    status: str
    created_at: datetime


class DocumentReviewIn(BaseModel):
    status: Literal["APPROVED", "REJECTED"]


class CrawlIn(BaseModel):
    urls: list[str] = Field(min_length=1)


class CrawlOut(BaseModel):
    inserted: int
    skipped: int
    documents: list[DocumentOut]


class CrawlPresetIn(BaseModel):
    # "who" là bí danh cũ của "vinmec", giữ để giao diện cũ không vỡ
    source: Literal["moh", "vinmec", "who", "all"] = "moh"
    limit: int = Field(default=10, ge=1, le=50)




# ---------- Audit ----------
class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: UUID | None
    action: str
    entity: str
    entity_id: str | None
    created_at: datetime


# ---------- Chat (Trợ lý AI) ----------
class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class CitationOut(BaseModel):
    """Nguồn trích dẫn — đúng hình dạng Chat.jsx đang đọc."""
    title: str
    url: str | None = None
    snippet: str | None = None


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    created_at: datetime
    citations: list[CitationOut] = []


class ChatReplyOut(BaseModel):
    reply: str
    citations: list[CitationOut] = []


# ---------- Vision & Meal Logging ----------
class MealAnalyzeOut(BaseModel):
    food_name: str
    calories_kcal: float
    protein_g: float
    carb_g: float
    fat_g: float
    description: str
    confidence: float


class MealLogIn(BaseModel):
    food_name: str
    calories_kcal: float = Field(ge=0)
    protein_g: float = Field(default=0.0)
    carb_g: float = Field(default=0.0)
    fat_g: float = Field(default=0.0)
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER", "SNACK"] = "LUNCH"
    quantity: float = Field(default=1.0, gt=0)
    log_date: date | None = None
