import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, String, Boolean, Integer, SmallInteger, Numeric, Date,
    DateTime, ForeignKey, Text, CHAR, Enum as SAEnum, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base

# Enum đã tồn tại trong DB → create_type=False để SQLAlchemy không tạo lại
user_role   = SAEnum("ADMIN", "EXPERT", "USER", name="user_role", create_type=False)
gender_enum = SAEnum("MALE", "FEMALE", "OTHER", name="gender_enum", create_type=False)
goal_enum   = SAEnum("LOSE_WEIGHT", "MAINTAIN", "GAIN_MUSCLE", "MEDICAL",
                     name="goal_enum", create_type=False)
plan_status = SAEnum("ACTIVE", "COMPLETED", "REVISED", "CANCELLED",
                     name="plan_status", create_type=False)


class Country(Base):
    __tablename__ = "countries"
    code = Column(CHAR(2), primary_key=True)
    name = Column(String(100), nullable=False)


class User(Base):
    __tablename__ = "users"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name     = Column(String(150))
    role          = Column(user_role, nullable=False, default="USER")
    country_code  = Column(CHAR(2), ForeignKey("countries.code"))
    is_active     = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at    = Column(DateTime(timezone=True))

    profile = relationship("HealthProfile", back_populates="user", uselist=False)


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                            unique=True, nullable=False)
    gender         = Column(gender_enum)
    birth_date     = Column(Date)
    height_cm      = Column(Numeric(5, 2))
    weight_kg      = Column(Numeric(5, 2))
    # generated column → chỉ đọc, KHÔNG bao giờ insert
    bmi            = Column(Numeric(5, 2))
    activity_level = Column(SmallInteger)
    goal           = Column(goal_enum, nullable=False, default="MAINTAIN")
    daily_calorie_target = Column(Integer)

    user = relationship("User", back_populates="profile")


class MedicalCondition(Base):
    __tablename__ = "medical_conditions"
    id   = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)


class Allergen(Base):
    __tablename__ = "allergens"
    id   = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)


class ProfileCondition(Base):
    __tablename__ = "profile_conditions"
    profile_id   = Column(UUID(as_uuid=True), ForeignKey("health_profiles.id", ondelete="CASCADE"),
                          primary_key=True)
    condition_id = Column(Integer, ForeignKey("medical_conditions.id", ondelete="CASCADE"),
                          primary_key=True)


class ProfileAllergen(Base):
    __tablename__ = "profile_allergens"
    profile_id  = Column(UUID(as_uuid=True), ForeignKey("health_profiles.id", ondelete="CASCADE"),
                         primary_key=True)
    allergen_id = Column(Integer, ForeignKey("allergens.id", ondelete="CASCADE"),
                         primary_key=True)
    severity    = Column(SmallInteger)


class NutritionPlan(Base):
    __tablename__ = "nutrition_plans"
    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id           = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    version           = Column(Integer, nullable=False, default=1)
    parent_plan_id    = Column(UUID(as_uuid=True), ForeignKey("nutrition_plans.id"))
    start_date        = Column(Date, nullable=False)
    end_date          = Column(Date, nullable=False)
    daily_kcal_target = Column(Integer, nullable=False)
    goal              = Column(goal_enum, nullable=False)
    content           = Column(JSONB, nullable=False)
    generated_by      = Column(String(100))
    status            = Column(plan_status, nullable=False, default="ACTIVE")
    created_at        = Column(DateTime(timezone=True), server_default=func.now())