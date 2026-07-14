from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


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
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    country_code: str = Field(min_length=2, max_length=2)
    profile: ProfileIn


class LoginIn(BaseModel):
    email: EmailStr
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