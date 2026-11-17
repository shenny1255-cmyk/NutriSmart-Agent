from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import MedicalCondition, Allergen, Food, Exercise
from app.schemas import ItemOut, FoodOut, ExerciseOut, FoodCompositionOut, FoodCompositionDetailOut
from app.services import food_composition

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

@router.get("/food-composition", response_model=list[FoodCompositionOut])
def food_composition_search(
    q: str | None = Query(None, description="tên thực phẩm, gõ có dấu hoặc không dấu"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Tra Bảng thành phần thực phẩm Việt Nam (Viện Dinh dưỡng 2007), giá trị/100 g ăn được."""
    return food_composition.search(db, q, limit)


@router.get("/food-composition/{code}", response_model=FoodCompositionDetailOut)
def food_composition_detail(
    code: str,
    grams: float | None = Query(None, gt=0, le=5000, description="quy đổi cho khẩu phần (gram ăn được)"),
    db: Session = Depends(get_db),
):
    row = food_composition.get(db, code)
    if row is None:
        raise HTTPException(404, "Không có thực phẩm này trong bảng")
    out = FoodCompositionDetailOut.model_validate(row)
    if grams is not None:
        out.per_portion = food_composition.scale(row, grams)
    return out
