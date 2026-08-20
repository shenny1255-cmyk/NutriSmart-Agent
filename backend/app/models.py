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
    role: str     = Column(
        user_role,
        ForeignKey("role_permissions.role"),
        nullable=False,
        default="USER",
    )  # type: ignore
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    profile       = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    staff_profile = relationship("StaffProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    role_permission = relationship("RolePermission", back_populates="users", uselist=False, lazy="joined")

    @property
    def full_name(self) -> str | None:
        return self.profile.full_name if self.profile else None

    @full_name.setter
    def full_name(self, value: str | None):
        if not self.profile:
            self.profile = UserProfile()
        self.profile.full_name = value


class UserProfile(Base):
    __tablename__ = "user_profile"
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    full_name: str | None = Column(String(150))  # type: ignore
    gender: str | None         = Column(gender_enum)  # type: ignore
    birth_date: date | None     = Column(Date)  # type: ignore
    activity_level_id: int | None = Column(
        SmallInteger,
        ForeignKey("activity_levels.id"),
    )  # type: ignore
    goal: str           = Column(goal_enum, nullable=False, default="MAINTAIN")  # type: ignore
    daily_calorie_target: int | None = Column(Integer)  # type: ignore
    custom_conditions = Column(JSONB, nullable=False, default=list, server_default="'[]'::jsonb")
    custom_allergens  = Column(JSONB, nullable=False, default=list, server_default="'[]'::jsonb")
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")
    conditions = relationship("MedicalCondition", secondary="user_medical_conditions",
                              lazy="selectin", viewonly=True)
    allergens  = relationship("Allergen", secondary="user_allergens",
                              lazy="selectin", viewonly=True)
    activity_level_ref = relationship("ActivityLevel", lazy="joined")

    @property
    def activity_level(self) -> int | None:
        """Tên tương thích cho API cũ; dữ liệu thật nằm ở activity_level_id."""
        return self.activity_level_id

    @activity_level.setter
    def activity_level(self, value: int | None) -> None:
        self.activity_level_id = value  # type: ignore


class ActivityLevel(Base):
    """Danh mục mức độ vận động và hệ số tính TDEE."""
    __tablename__ = "activity_levels"
    id: int = Column(SmallInteger, primary_key=True, autoincrement=False)  # type: ignore
    name: str = Column(String(100), unique=True, nullable=False)  # type: ignore
    description: str | None = Column(String(500))  # type: ignore
    calorie_multiplier: float = Column(Numeric(4, 3), nullable=False)  # type: ignore


class StaffProfile(Base):
    __tablename__ = "staff_profiles"
    user_id            = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    staff_code: str    = Column(String(30), unique=True, nullable=False)  # type: ignore
    full_name: str     = Column(String(150), nullable=False)  # type: ignore
    gender: str | None = Column(String(10))  # type: ignore
    birth_date: date | None = Column(Date)  # type: ignore
    specialization: str | None = Column(String(100))  # type: ignore
    qualification: str | None  = Column(String(100))  # type: ignore
    employment_status: str     = Column(String(20), nullable=False, default="ACTIVE")  # type: ignore
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
    updated_at         = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user        = relationship("User", back_populates="staff_profile")


class RolePermission(Base):
    """Bộ quyền dùng chung cho toàn bộ tài khoản có cùng vai trò."""
    __tablename__ = "role_permissions"
    role: str = Column(user_role, primary_key=True)  # type: ignore
    can_manage_users: bool       = Column(Boolean, nullable=False, default=False)  # type: ignore
    can_manage_foods: bool       = Column(Boolean, nullable=False, default=False)  # type: ignore
    can_manage_categories: bool  = Column(Boolean, nullable=False, default=False)  # type: ignore
    can_review_documents: bool   = Column(Boolean, nullable=False, default=False)  # type: ignore
    can_review_plans: bool       = Column(Boolean, nullable=False, default=False)  # type: ignore
    can_review_ai_chat: bool     = Column(Boolean, nullable=False, default=False)  # type: ignore
    can_review_logs: bool        = Column(Boolean, nullable=False, default=False)  # type: ignore
    can_manage_permissions: bool = Column(Boolean, nullable=False, default=False)  # type: ignore
    created_at             = Column(DateTime(timezone=True), server_default=func.now())
    updated_at             = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="role_permission")


class MedicalCondition(Base):
    __tablename__ = "medical_conditions"
    id   = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)


class Allergen(Base):
    __tablename__ = "allergens"
    id   = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False)


class UserMedicalCondition(Base):
    __tablename__ = "user_medical_conditions"
    user_id      = Column(UUID(as_uuid=True), ForeignKey("user_profile.user_id", ondelete="CASCADE"), primary_key=True)
    condition_id = Column(Integer, ForeignKey("medical_conditions.id", ondelete="CASCADE"), primary_key=True)


class UserAllergen(Base):
    __tablename__ = "user_allergens"
    user_id     = Column(UUID(as_uuid=True), ForeignKey("user_profile.user_id", ondelete="CASCADE"), primary_key=True)
    allergen_id = Column(Integer, ForeignKey("allergens.id", ondelete="CASCADE"), primary_key=True)


class NutritionPlan(Base):
    __tablename__ = "nutrition_plans"
    id: uuid.UUID     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    user_id           = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    parent_plan_id    = Column(UUID(as_uuid=True), ForeignKey("nutrition_plans.id", ondelete="SET NULL"))
    version           = Column(Integer, nullable=False, default=1)
    start_date: date  = Column(Date, nullable=False)  # type: ignore
    end_date: date    = Column(Date, nullable=False)  # type: ignore
    daily_kcal_target: int = Column(Integer, nullable=False)  # type: ignore
    goal: str         = Column(goal_enum, nullable=False)  # type: ignore
    content           = Column(JSONB, nullable=False)
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
    """Số đo cơ thể theo ngày — mỗi lần thay đổi đều giữ lại được lịch sử."""
    __tablename__ = "body_metrics_history"
    id: int          = Column(BigInteger, primary_key=True, autoincrement=True)  # type: ignore
    user_id: uuid.UUID = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # type: ignore
    recorded_at: date = Column(Date, nullable=False, server_default=func.current_date())  # type: ignore
    height_cm: float | None = Column(Numeric(5, 2))  # type: ignore
    weight_kg: float | None = Column(Numeric(5, 2))  # type: ignore

    @property
    def bmi(self) -> float | None:
        """Tính BMI từ số đo tại chính mốc lịch sử này."""
        if self.height_cm and self.weight_kg and float(self.height_cm) > 0:
            return round(float(self.weight_kg) / ((float(self.height_cm) / 100) ** 2), 2)
        return None


class PlanCheckinSeries(Base):
    """Chuỗi các kỳ check-in liên tục theo cùng một mục tiêu."""
    __tablename__ = "plan_checkin_series"
    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    goal: str     = Column(goal_enum, nullable=False)  # type: ignore
    status: str   = Column(String(20), nullable=False, default="ACTIVE")  # type: ignore
    started_at: date = Column(Date, nullable=False)  # type: ignore
    duration_months: int = Column(SmallInteger, nullable=False, default=3)  # type: ignore
    planned_end_date: date = Column(Date, nullable=False)  # type: ignore
    closed_at: date | None = Column(Date)  # type: ignore
    completed_at           = Column(DateTime(timezone=True))
    completion_reason: str | None = Column(String(30))  # type: ignore
    created_at    = Column(DateTime(timezone=True), server_default=func.now())


class PlanCheckin(Base):
    """Snapshot, dữ liệu thực tế và kết quả một kỳ coaching 14 ngày."""
    __tablename__ = "plan_checkins"
    id: uuid.UUID             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    series_id                 = Column(UUID(as_uuid=True), ForeignKey("plan_checkin_series.id", ondelete="CASCADE"), nullable=False)
    user_id                   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id                   = Column(UUID(as_uuid=True), ForeignKey("nutrition_plans.id", ondelete="CASCADE"), nullable=False)
    adjusted_plan_id          = Column(UUID(as_uuid=True), ForeignKey("nutrition_plans.id", ondelete="SET NULL"))
    previous_checkin_id       = Column(UUID(as_uuid=True), ForeignKey("plan_checkins.id", ondelete="SET NULL"))
    period_number: int        = Column(Integer, nullable=False)  # type: ignore
    start_date: date          = Column(Date, nullable=False)  # type: ignore
    period_end: date          = Column(Date, nullable=False)  # type: ignore
    due_date: date            = Column(Date, nullable=False)  # type: ignore
    grace_until: date         = Column(Date, nullable=False)  # type: ignore
    baseline_weight_kg: float = Column(Numeric(5, 2), nullable=False)  # type: ignore
    baseline_waist_cm: float | None = Column(Numeric(5, 2))  # type: ignore
    goal_snapshot: str        = Column(goal_enum, nullable=False)  # type: ignore
    target_kcal_snapshot: int = Column(Integer, nullable=False)  # type: ignore
    activity_target_snapshot: int | None = Column(SmallInteger)  # type: ignore
    expected_weight_min_kg: float = Column(Numeric(5, 2), nullable=False)  # type: ignore
    expected_weight_max_kg: float = Column(Numeric(5, 2), nullable=False)  # type: ignore
    prediction_rule_version: str = Column(String(30), nullable=False)  # type: ignore
    actual_weight_kg: float | None = Column(Numeric(5, 2))  # type: ignore
    actual_waist_cm: float | None = Column(Numeric(5, 2))  # type: ignore
    actual_activity_level: int | None = Column(SmallInteger)  # type: ignore
    adherence_pct: int | None = Column(SmallInteger)  # type: ignore
    energy_level: int | None = Column(SmallInteger)  # type: ignore
    hunger_level: int | None = Column(SmallInteger)  # type: ignore
    sleep_quality: int | None = Column(SmallInteger)  # type: ignore
    notes: str | None         = Column(String(1000))  # type: ignore
    meal_log_days: int | None = Column(SmallInteger)  # type: ignore
    avg_kcal_intake: float | None = Column(Numeric(8, 2))  # type: ignore
    weight_change_kg: float | None = Column(Numeric(5, 2))  # type: ignore
    data_quality_result: str | None = Column(String(30))  # type: ignore
    adherence_result: str | None = Column(String(20))  # type: ignore
    outcome_result: str | None = Column(String(30))  # type: ignore
    safety_flags             = Column(JSONB, nullable=False, default=list)
    recommendation: str | None = Column(String(30))  # type: ignore
    recommendation_reason: str | None = Column(Text)  # type: ignore
    proposed_kcal_target: int | None = Column(Integer)  # type: ignore
    ai_feedback: str | None = Column(Text)  # type: ignore
    feedback_status: str    = Column(String(20), nullable=False, default="NOT_REQUESTED")  # type: ignore
    status: str             = Column(String(20), nullable=False, default="OPEN")  # type: ignore
    decision: str | None    = Column(String(30))  # type: ignore
    submitted_at            = Column(DateTime(timezone=True))
    completed_at            = Column(DateTime(timezone=True))
    decision_at             = Column(DateTime(timezone=True))
    adjustment_applied_at   = Column(DateTime(timezone=True))
    created_at              = Column(DateTime(timezone=True), server_default=func.now())
    updated_at              = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PlanDailyProgress(Base):
    """Tiến độ bốn mục của một ngày thực tế trong một Đợt."""
    __tablename__ = "plan_daily_progress"
    id: uuid.UUID             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    user_id                   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    series_id                 = Column(UUID(as_uuid=True), ForeignKey("plan_checkin_series.id", ondelete="CASCADE"), nullable=False)
    checkin_id                = Column(UUID(as_uuid=True), ForeignKey("plan_checkins.id", ondelete="CASCADE"), nullable=False)
    plan_id                   = Column(UUID(as_uuid=True), ForeignKey("nutrition_plans.id", ondelete="CASCADE"), nullable=False)
    progress_date: date       = Column(Date, nullable=False)  # type: ignore
    template_day_index: int   = Column(SmallInteger, nullable=False)  # type: ignore
    checked_items             = Column(JSONB, nullable=False, default=list, server_default="'[]'::jsonb")
    status: str               = Column(String(20), nullable=False, default="IN_PROGRESS")  # type: ignore
    completed_at              = Column(DateTime(timezone=True))
    created_at                = Column(DateTime(timezone=True), server_default=func.now())
    updated_at                = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Notification(Base):
    """Thông báo hệ thống gửi tới người dùng."""
    __tablename__ = "notifications"
    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type       = Column(String(50), nullable=False)
    title      = Column(String(200), nullable=False)
    body       = Column(Text)
    dedupe_key = Column(String(150))
    is_read: bool = Column(Boolean, nullable=False, default=False)  # type: ignore
    created_at = Column(DateTime(timezone=True), server_default=func.now())

from sqlalchemy import Enum as SAEnum

doc_status  = SAEnum("DRAFT", "PENDING", "APPROVED", "REJECTED",
                     name="doc_status", create_type=False)


class DocCategory(Base):
    __tablename__ = "doc_categories"
    id: int          = Column(Integer, primary_key=True)  # type: ignore
    parent_id: int | None = Column(Integer, ForeignKey("doc_categories.id", ondelete="SET NULL"))  # type: ignore
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
    started_at           = Column(DateTime(timezone=True))
    ended_at             = Column(DateTime(timezone=True))
    logged_at            = Column(DateTime(timezone=True), server_default=func.now())
    source_type: str | None = Column(String(20))  # type: ignore
    source_progress_id    = Column(UUID(as_uuid=True), ForeignKey("plan_daily_progress.id", ondelete="SET NULL"))
    source_item_key: str | None = Column(String(30))  # type: ignore
    item_name_snapshot: str | None = Column(String(200))  # type: ignore


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
    source_type: str | None = Column(String(20))  # type: ignore
    source_progress_id = Column(UUID(as_uuid=True), ForeignKey("plan_daily_progress.id", ondelete="SET NULL"))
    source_item_key: str | None = Column(String(30))  # type: ignore
    item_name_snapshot: str | None = Column(String(200))  # type: ignore


class CrawlSource(Base):
    """Nguồn cào dữ liệu y khoa tự động."""
    __tablename__ = "crawl_sources"
    id: uuid.UUID   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    name: str       = Column(String(255), nullable=False)  # type: ignore
    source_key: str = Column(String(100), unique=True, nullable=False)  # type: ignore
    domain: str     = Column(String(255), nullable=False)  # type: ignore
    base_urls       = Column(JSONB, nullable=False, default=list)
    is_active: bool = Column(Boolean, nullable=False, default=True)  # type: ignore
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


