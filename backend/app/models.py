import uuid
from datetime import datetime, date
from sqlalchemy import Enum as SAEnum

from sqlalchemy import (
    Column, String, Boolean, Integer, BigInteger, SmallInteger, Numeric, Date,
    DateTime, ForeignKey, Text, CHAR, Enum as SAEnum, func, FetchedValue
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.database import Base

# Enum đã tồn tại trong DB → create_type=False để SQLAlchemy không tạo lại
user_role   = SAEnum("ADMIN", "EXPERT", "USER", name="user_role", create_type=False)
gender_enum = SAEnum("MALE", "FEMALE", "OTHER", name="gender_enum", create_type=False)
goal_enum   = SAEnum("LOSE_WEIGHT", "MAINTAIN", "GAIN_MUSCLE", "MEDICAL",
                     name="goal_enum", create_type=False)
plan_status = SAEnum("ACTIVE", "COMPLETED", "REVISED", "CANCELLED",
                     name="plan_status", create_type=False)
eval_result = SAEnum("ACHIEVED", "NOT_ACHIEVED", "PARTIAL",
                     name="eval_result", create_type=False)


class Country(Base):
    __tablename__ = "countries"
    code = Column(CHAR(2), primary_key=True)
    name = Column(String(100), nullable=False)


class User(Base):
    __tablename__ = "users"
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    email         = Column(String(255), unique=True, nullable=False)
    password_hash: str = Column(String(255), nullable=False)  # type: ignore
    full_name     = Column(String(150))
    role          = Column(user_role, nullable=False, default="USER")
    country_code  = Column(CHAR(2), ForeignKey("countries.code"))
    is_active: bool = Column(Boolean, nullable=False, default=True)  # type: ignore
    email_verified: bool = Column(Boolean, nullable=False, server_default="false")  # type: ignore
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at    = Column(DateTime(timezone=True))

    profile = relationship("HealthProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


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
    bmi            = Column(Numeric(5, 2), server_default=FetchedValue())
    activity_level = Column(SmallInteger)
    goal           = Column(goal_enum, nullable=False, default="MAINTAIN")
    daily_calorie_target = Column(Integer)

    user = relationship("User", back_populates="profile")
    # Bệnh nền + dị ứng — nạp sẵn để prompt LLM luôn có đủ ràng buộc sức khỏe
    conditions = relationship("MedicalCondition", secondary="profile_conditions",
                              lazy="selectin", viewonly=True)
    allergens  = relationship("Allergen", secondary="profile_allergens",
                              lazy="selectin", viewonly=True)


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
    id: uuid.UUID     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    user_id           = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    version           = Column(Integer, nullable=False, default=1)
    parent_plan_id    = Column(UUID(as_uuid=True), ForeignKey("nutrition_plans.id"))
    start_date: date  = Column(Date, nullable=False)  # type: ignore
    end_date: date    = Column(Date, nullable=False)  # type: ignore
    daily_kcal_target: int = Column(Integer, nullable=False)  # type: ignore
    goal: str         = Column(goal_enum, nullable=False)  # type: ignore
    content           = Column(JSONB, nullable=False)
    generated_by      = Column(String(100))
    status: str       = Column(plan_status, nullable=False, default="ACTIVE")  # type: ignore
    created_at        = Column(DateTime(timezone=True), server_default=func.now())


class PlanEvaluation(Base):
    """Kết quả chấm một chu kỳ 7 ngày của lộ trình (job đánh giá sinh ra)."""
    __tablename__ = "plan_evaluations"
    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    plan_id          = Column(UUID(as_uuid=True), ForeignKey("nutrition_plans.id", ondelete="CASCADE"),
                              nullable=False)
    period_start: date = Column(Date, nullable=False)  # type: ignore
    period_end: date   = Column(Date, nullable=False)  # type: ignore
    avg_kcal_intake: float  = Column(Numeric(8, 2))  # type: ignore
    weight_change_kg: float = Column(Numeric(5, 2))  # type: ignore
    result: str      = Column(eval_result, nullable=False)  # type: ignore
    ai_feedback      = Column(Text)
    evaluated_at     = Column(DateTime(timezone=True), server_default=func.now())


class BodyMetricHistory(Base):
    """Mốc cân nặng theo ngày — dùng để tính weight_change_kg giữa 2 kỳ đánh giá."""
    __tablename__ = "body_metrics_history"
    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recorded_at = Column(Date, nullable=False, server_default=func.current_date())
    weight_kg   = Column(Numeric(5, 2))
    bmi         = Column(Numeric(5, 2))

from sqlalchemy import Enum as SAEnum

doc_status  = SAEnum("DRAFT", "PENDING", "APPROVED", "REJECTED",
                     name="doc_status", create_type=False)
drug_status = SAEnum("ALLOWED", "RESTRICTED", "BANNED",
                     name="drug_status", create_type=False)


class DocCategory(Base):
    __tablename__ = "doc_categories"
    id        = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("doc_categories.id"))
    name      = Column(String(150), nullable=False)
    slug      = Column(String(150), unique=True, nullable=False)


class Document(Base):
    __tablename__ = "documents"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(Integer, ForeignKey("doc_categories.id"))
    title       = Column(Text, nullable=False)
    source_url  = Column(Text)
    source_name = Column(String(150))
    language    = Column(String(10), default="vi")
    file_path   = Column(Text)
    raw_text    = Column(Text)
    status      = Column(doc_status, nullable=False, default="PENDING")
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at  = Column(DateTime(timezone=True))


class DocChunk(Base):
    __tablename__ = "doc_chunks"
    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content     = Column(Text, nullable=False)
    token_count = Column(Integer)
    embedding   = Column(Vector(1024))
    metadata_   = Column("metadata", JSONB, server_default=FetchedValue())

    document    = relationship("Document")


class DrugCategory(Base):
    __tablename__ = "drug_categories"
    id   = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)


class Drug(Base):
    __tablename__ = "drugs"
    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id       = Column(Integer, ForeignKey("drug_categories.id"))
    name              = Column(String(200), nullable=False)
    active_ingredient = Column(String(200))
    indications       = Column(Text)
    side_effects      = Column(Text)
    contraindications = Column(Text)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at        = Column(DateTime(timezone=True))

    rules             = relationship("DrugCountryRule", lazy="selectin", cascade="all, delete-orphan")


class DrugCountryRule(Base):
    __tablename__ = "drug_country_rules"
    drug_id      = Column(UUID(as_uuid=True), ForeignKey("drugs.id", ondelete="CASCADE"),
                          primary_key=True)
    country_code = Column(CHAR(2), ForeignKey("countries.code", ondelete="CASCADE"),
                          primary_key=True)
    status       = Column(drug_status, nullable=False, default="ALLOWED")
    note         = Column(Text)
    updated_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_at   = Column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id         = Column(Integer, primary_key=True)   # BIGSERIAL, dùng Integer là đủ ở ORM
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role       = Column(String(20), nullable=False)
    content    = Column(Text, nullable=False)
    flagged    = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id          = Column(Integer, primary_key=True)
    actor_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action      = Column(String(50), nullable=False)
    entity      = Column(String(80), nullable=False)
    entity_id   = Column(Text)
    before_data = Column(JSONB)
    after_data  = Column(JSONB)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False)
    title      = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Exercise(Base):
    __tablename__ = "exercises"
    id        = Column(Integer, primary_key=True)
    name      = Column(String(150), nullable=False)
    met_value = Column(Numeric(4, 2))
    category  = Column(String(80))


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exercise_id     = Column(Integer, ForeignKey("exercises.id"), nullable=True)
    steps           = Column(Integer, default=0)
    duration_min    = Column(Integer, default=0)
    calories_burned = Column(Numeric(7, 2), default=0)
    log_date        = Column(Date, nullable=False, server_default=func.current_date())


meal_type_enum = SAEnum("BREAKFAST", "LUNCH", "DINNER", "SNACK", name="meal_type", create_type=False)


class Food(Base):
    __tablename__ = "foods"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name          = Column(String(200), nullable=False)
    serving_desc  = Column(String(100))
    serving_gram  = Column(Numeric(7, 2))
    calories_kcal = Column(Numeric(7, 2), nullable=False)
    protein_g     = Column(Numeric(6, 2), default=0)
    carb_g        = Column(Numeric(6, 2), default=0)
    fat_g         = Column(Numeric(6, 2), default=0)
    source        = Column(String(100), default="AI Gemini")


class MealLog(Base):
    __tablename__ = "meal_logs"
    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    food_id       = Column(UUID(as_uuid=True), ForeignKey("foods.id"), nullable=True)
    meal_type     = Column(meal_type_enum, nullable=False, default="LUNCH")
    quantity      = Column(Numeric(6, 2), nullable=False, default=1)
    calories_kcal = Column(Numeric(7, 2), nullable=False)
    logged_at     = Column(DateTime(timezone=True), server_default=func.now())
    log_date      = Column(Date, nullable=False, server_default=func.current_date())
