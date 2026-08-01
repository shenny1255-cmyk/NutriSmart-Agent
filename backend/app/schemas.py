from datetime import date
from typing import Annotated, Literal
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict, BeforeValidator


def _normalize_email(v: str) -> str:
    """Trim + thường hoá email trước khi EmailStr kiểm tra → không phân biệt hoa/thường."""
    return v.strip().lower() if isinstance(v, str) else v


# Chấp nhận MỌI nhà cung cấp (EmailStr không chặn theo domain), luôn lưu ở dạng chuẩn hoá.
NormalizedEmail = Annotated[EmailStr, BeforeValidator(_normalize_email)]


# ---------- Register ----------
class ProfileIn(BaseModel):
    gender: Literal["MALE", "FEMALE", "OTHER"]
    birth_date: date
    height_cm: float = Field(gt=50, lt=250)
    weight_kg: float = Field(gt=20, lt=300)
    activity_level: int = Field(ge=1, le=5)
    goal: Literal["LOSE_WEIGHT", "MAINTAIN", "GAIN_MUSCLE", "MEDICAL"]
    condition_ids: list[int] = []
    allergen_ids: list[int] = []


class RegisterIn(BaseModel):
    email: NormalizedEmail
    password: str = Field(min_length=8)
    full_name: str
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


# ---------- User ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    full_name: str | None = None
    role: str
    is_verified: bool = False


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    gender: str | None
    birth_date: date | None
    height_cm: float | None
    weight_kg: float | None
    bmi: float | None
    activity_level: int | None
    goal: str | None
    daily_calorie_target: int | None
    conditions: list[ItemOut] = []
    allergens: list[ItemOut] = []


class MeOut(UserOut):
    """GET /auth/me trả về kèm hồ sơ sức khỏe để frontend dùng."""
    profile: ProfileOut | None = None


class UserProfileUpdateIn(BaseModel):
    """Cập nhật thông tin cá nhân + hồ sơ sức khỏe."""
    full_name: str | None = None
    # Hồ sơ sức khỏe
    gender: Literal["MALE", "FEMALE", "OTHER"] | None = None
    birth_date: date | None = None
    height_cm: float | None = Field(default=None, gt=50, lt=250)
    weight_kg: float | None = Field(default=None, gt=20, lt=300)
    activity_level: int | None = Field(default=None, ge=1, le=5)
    goal: Literal["LOSE_WEIGHT", "MAINTAIN", "GAIN_MUSCLE", "MEDICAL"] | None = None
    condition_ids: list[int] | None = None
    allergen_ids: list[int] | None = None


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
    food_name: str | None = Field(default=None, max_length=200)
    calories_kcal: float | None = Field(default=None, ge=0)
    protein_g: float = Field(default=0.0, ge=0)
    carb_g: float = Field(default=0.0, ge=0)
    fat_g: float = Field(default=0.0, ge=0)
    meal_type: Literal["BREAKFAST", "LUNCH", "DINNER", "SNACK"] = "LUNCH"
    quantity: float = Field(default=1.0, gt=0)
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
    log_date: date | None = None


class ActivityLogOut(BaseModel):
    id: int
    exercise_name: str
    duration_min: int
    calories_burned: float
    steps: int
    log_date: date


class WeightIn(BaseModel):
    weight_kg: float = Field(gt=20, lt=400)
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


class DrugCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    so_thuoc: int = 0


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




# ---------- Drugs ----------
class DrugIn(BaseModel):
    category_id: int | None = None
    document_id: UUID | None = None
    name: str
    active_ingredient: str | None = None
    indications: str | None = None
    side_effects: str | None = None
    contraindications: str | None = None
    status: Literal["ALLOWED", "RESTRICTED", "BANNED"] = "ALLOWED"
    status_note: str | None = None


class DrugOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    active_ingredient: str | None
    category_id: int | None
    document_id: UUID | None
    indications: str | None
    side_effects: str | None
    contraindications: str | None
    status: str
    status_note: str | None


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
