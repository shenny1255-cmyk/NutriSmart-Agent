import uuid
from datetime import datetime, date
from sqlalchemy import Enum as SAEnum

from sqlalchemy import (
    Column, String, Boolean, Integer, BigInteger, SmallInteger, Numeric, Date,
    DateTime, ForeignKey, Text, CHAR, Enum as SAEnum, func, FetchedValue
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
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
job_status  = SAEnum("QUEUED", "RUNNING", "DONE", "FAILED",
                     name="job_status", create_type=False)


class User(Base):
    __tablename__ = "users"
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    email: str    = Column(String(255), unique=True, nullable=False)  # type: ignore
    password_hash: str = Column(String(255), nullable=False)  # type: ignore
    role: str     = Column(user_role, nullable=False, default="USER")  # type: ignore
    is_verified: bool = Column(Boolean, nullable=False, server_default="false")  # type: ignore
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    profile = relationship("HealthProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    info    = relationship("UserInfo", back_populates="user", uselist=False, cascade="all, delete-orphan")

    @property
    def full_name(self) -> str | None:
        return self.info.full_name if self.info else None

    @full_name.setter
    def full_name(self, value: str | None):
        if not self.info:
            self.info = UserInfo()
        self.info.full_name = value


class UserInfo(Base):
    __tablename__ = "user_info"
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    full_name: str | None = Column(String(150))  # type: ignore
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="info")


class HealthProfile(Base):
    __tablename__ = "health_profiles"
    id: uuid.UUID  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    user_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                            unique=True, nullable=False)  # type: ignore
    gender: str | None         = Column(gender_enum)  # type: ignore
    birth_date: date | None     = Column(Date)  # type: ignore
    height_cm: float | None      = Column(Numeric(5, 2))  # type: ignore
    weight_kg: float | None      = Column(Numeric(5, 2))  # type: ignore
    # generated column → chỉ đọc, KHÔNG bao giờ insert
    bmi: float | None            = Column(Numeric(5, 2), server_default=FetchedValue())  # type: ignore
    activity_level: int | None = Column(SmallInteger)  # type: ignore
    goal: str           = Column(goal_enum, nullable=False, default="MAINTAIN")  # type: ignore
    daily_calorie_target: int | None = Column(Integer)  # type: ignore
    updated_at     = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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
    id: int          = Column(BigInteger, primary_key=True, autoincrement=True)  # type: ignore
    user_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # type: ignore
    recorded_at: date = Column(Date, nullable=False, server_default=func.current_date())  # type: ignore
    weight_kg: float | None = Column(Numeric(5, 2))  # type: ignore
    bmi: float | None = Column(Numeric(5, 2))  # type: ignore


class Notification(Base):
    """Thông báo hệ thống gửi tới người dùng."""
    __tablename__ = "notifications"
    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type       = Column(String(50), nullable=False)
    title      = Column(String(200), nullable=False)
    body       = Column(Text)
    is_read: bool = Column(Boolean, nullable=False, default=False)  # type: ignore
    created_at = Column(DateTime(timezone=True), server_default=func.now())

from sqlalchemy import Enum as SAEnum

doc_status  = SAEnum("DRAFT", "PENDING", "APPROVED", "REJECTED",
                     name="doc_status", create_type=False)
drug_status = SAEnum("ALLOWED", "RESTRICTED", "BANNED",
                     name="drug_status", create_type=False)


class DocCategory(Base):
    __tablename__ = "doc_categories"
    id: int          = Column(Integer, primary_key=True)  # type: ignore
    parent_id: int | None = Column(Integer, ForeignKey("doc_categories.id"))  # type: ignore
    name: str        = Column(String(150), nullable=False)  # type: ignore
    slug: str        = Column(String(150), unique=True, nullable=False)  # type: ignore


class Document(Base):
    __tablename__ = "documents"
    id: uuid.UUID   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    category_id: int | None = Column(Integer, ForeignKey("doc_categories.id"))  # type: ignore
    title: str       = Column(Text, nullable=False)  # type: ignore
    source_url: str | None  = Column(Text)  # type: ignore
    source_name: str | None = Column(String(150))  # type: ignore
    language: str    = Column(String(10), default="vi")  # type: ignore
    file_path: str | None   = Column(Text)  # type: ignore
    raw_text: str | None    = Column(Text)  # type: ignore
    status: str      = Column(doc_status, nullable=False, default="PENDING")  # type: ignore
    uploaded_by: uuid.UUID | None = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # type: ignore
    approved_by: uuid.UUID | None = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # type: ignore
    approved_at      = Column(DateTime(timezone=True))
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at       = Column(DateTime(timezone=True))


class DocChunk(Base):
    __tablename__ = "doc_chunks"
    id: int          = Column(BigInteger, primary_key=True, autoincrement=True)  # type: ignore
    document_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)  # type: ignore
    chunk_index: int = Column(Integer, nullable=False)  # type: ignore
    content: str     = Column(Text, nullable=False)  # type: ignore
    token_count: int | None = Column(Integer)  # type: ignore
    embedding        = Column(Vector(1024))
    metadata_        = Column("metadata", JSONB, server_default=FetchedValue())

    document         = relationship("Document")


class DrugCategory(Base):
    __tablename__ = "drug_categories"
    id: int   = Column(Integer, primary_key=True)  # type: ignore
    name: str = Column(String(150), unique=True, nullable=False)  # type: ignore


class Drug(Base):
    __tablename__ = "drugs"
    id: uuid.UUID                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    category_id: int | None       = Column(Integer, ForeignKey("drug_categories.id"))  # type: ignore
    document_id: uuid.UUID | None       = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"))  # type: ignore
    name: str              = Column(String(200), nullable=False)  # type: ignore
    active_ingredient: str | None = Column(String(200))  # type: ignore
    indications: str | None       = Column(Text)  # type: ignore
    side_effects: str | None      = Column(Text)  # type: ignore
    contraindications: str | None = Column(Text)  # type: ignore
    status: str            = Column(drug_status, nullable=False, default="ALLOWED")  # type: ignore
    status_note: str | None       = Column(Text)  # type: ignore
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    deleted_at        = Column(DateTime(timezone=True))

    document          = relationship("Document")


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
    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action      = Column(String(50), nullable=False)
    entity      = Column(String(80), nullable=False)
    entity_id   = Column(Text)
    before_data = Column(JSONB)
    after_data  = Column(JSONB)
    ip_address  = Column(INET)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False)
    title      = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MessageCitation(Base):
    """Trích dẫn nguồn tài liệu cho từng tin nhắn AI trong chat."""
    __tablename__ = "message_citations"
    message_id = Column(BigInteger, ForeignKey("chat_messages.id", ondelete="CASCADE"),
                        primary_key=True)
    chunk_id   = Column(BigInteger, ForeignKey("doc_chunks.id", ondelete="CASCADE"),
                        primary_key=True)
    score      = Column(Numeric(5, 4))
    rank       = Column(SmallInteger)


class Exercise(Base):
    __tablename__ = "exercises"
    id: int        = Column(Integer, primary_key=True)  # type: ignore
    name: str      = Column(String(150), nullable=False)  # type: ignore
    met_value: float = Column(Numeric(4, 2))  # type: ignore
    category: str | None = Column(String(80))  # type: ignore


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id: int              = Column(BigInteger, primary_key=True, autoincrement=True)  # type: ignore
    user_id: uuid.UUID   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # type: ignore
    exercise_id: int | None = Column(Integer, ForeignKey("exercises.id"), nullable=True)  # type: ignore
    steps: int | None    = Column(Integer, default=0)  # type: ignore
    duration_min: int | None = Column(Integer, default=0)  # type: ignore
    calories_burned: float | None = Column(Numeric(7, 2), default=0)  # type: ignore
    log_date: date       = Column(Date, nullable=False, server_default=func.current_date())  # type: ignore


meal_type_enum = SAEnum("BREAKFAST", "LUNCH", "DINNER", "SNACK", name="meal_type", create_type=False)


class MealImage(Base):
    """Ảnh bữa ăn được phân tích bởi AI Vision — một ảnh có thể sinh ra nhiều meal_logs."""
    __tablename__ = "meal_images"
    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id           = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                               nullable=False)
    image_path        = Column(Text, nullable=False)
    status            = Column(job_status, nullable=False, default="QUEUED")
    predicted_food_id = Column(UUID(as_uuid=True), ForeignKey("foods.id"))
    confidence        = Column(Numeric(4, 3))
    raw_prediction    = Column(JSONB)
    estimated_kcal    = Column(Numeric(7, 2))
    suitability_note  = Column(Text)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())


class Food(Base):
    __tablename__ = "foods"
    id: uuid.UUID  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    name: str      = Column(String(200), nullable=False)  # type: ignore
    serving_desc: str | None = Column(String(100))  # type: ignore
    serving_gram: float | None = Column(Numeric(7, 2))  # type: ignore
    calories_kcal: float = Column(Numeric(7, 2), nullable=False)  # type: ignore
    protein_g: float = Column(Numeric(6, 2), default=0)  # type: ignore
    carb_g: float    = Column(Numeric(6, 2), default=0)  # type: ignore
    fat_g: float     = Column(Numeric(6, 2), default=0)  # type: ignore
    source: str      = Column(String(100), default="AI Gemini")  # type: ignore


class MealLog(Base):
    __tablename__ = "meal_logs"
    id: int            = Column(BigInteger, primary_key=True, autoincrement=True)  # type: ignore
    user_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # type: ignore
    food_id: uuid.UUID | None = Column(UUID(as_uuid=True), ForeignKey("foods.id"), nullable=True)  # type: ignore
    meal_image_id: uuid.UUID | None = Column(UUID(as_uuid=True), ForeignKey("meal_images.id"), nullable=True)  # type: ignore
    meal_type: str     = Column(meal_type_enum, nullable=False)  # type: ignore
    quantity: float    = Column(Numeric(6, 2), nullable=False, default=1)  # type: ignore
    calories_kcal: float = Column(Numeric(7, 2), nullable=False)  # type: ignore
    logged_at          = Column(DateTime(timezone=True), server_default=func.now())
    log_date: date     = Column(Date, nullable=False, server_default=func.current_date())  # type: ignore
