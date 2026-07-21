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
    country_code: str = Field(min_length=2, max_length=2)
    profile: ProfileIn


class LoginIn(BaseModel):
    email: NormalizedEmail
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Catalog ----------
class CountryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


# ---------- User ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    full_name: str | None
    role: str
    country_code: str | None


# ---------- Tracking ----------
class DailySummaryOut(BaseModel):
    day: date
    kcal_intake: float
    kcal_burned: float
    daily_calorie_target: int | None
    kcal_remaining: float | None
class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime


class UpdateRoleIn(BaseModel):
    role: Literal["ADMIN", "EXPERT", "USER"]


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
    source: Literal["moh", "who", "all"] = "moh"
    limit: int = Field(default=10, ge=1, le=50)




# ---------- Drugs ----------
class DrugIn(BaseModel):
    category_id: int | None = None
    name: str
    active_ingredient: str | None = None
    indications: str | None = None
    side_effects: str | None = None


class DrugOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    active_ingredient: str | None
    category_id: int | None


class DrugRuleIn(BaseModel):
    country_code: str = Field(min_length=2, max_length=2)
    status: Literal["ALLOWED", "RESTRICTED", "BANNED"]
    note: str | None = None


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


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    created_at: datetime


class ChatReplyOut(BaseModel):
    reply: str