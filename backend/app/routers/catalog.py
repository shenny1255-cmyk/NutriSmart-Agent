from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import MedicalCondition, Allergen, Food, Exercise
from app.schemas import ItemOut, FoodOut, ExerciseOut

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/conditions", response_model=list[ItemOut])
def conditions(db: Session = Depends(get_db)):
    return db.query(MedicalCondition).order_by(MedicalCondition.name).all()


@router.get("/allergens", response_model=list[ItemOut])
def allergens(db: Session = Depends(get_db)):
    return db.query(Allergen).order_by(Allergen.name).all()


@router.get("/foods", response_model=list[FoodOut])
def foods(
    q: str | None = Query(None, description="lọc theo tên món"),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Danh mục món ăn cho màn ghi nhật ký (có index trigram trên foods.name)."""
    query = db.query(Food)
    if q and q.strip():
        query = query.filter(Food.name.ilike(f"%{q.strip()}%"))  # type: ignore
    return query.order_by(Food.name).limit(limit).all()


@router.get("/exercises", response_model=list[ExerciseOut])
def exercises(db: Session = Depends(get_db)):
    return db.query(Exercise).order_by(Exercise.name).all()