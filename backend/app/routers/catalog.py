from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models import Country, MedicalCondition, Allergen
from app.schemas import CountryOut, ItemOut

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/countries", response_model=list[CountryOut])
def countries(db: Session = Depends(get_db)):
    return db.query(Country).order_by(Country.name).all()


@router.get("/conditions", response_model=list[ItemOut])
def conditions(db: Session = Depends(get_db)):
    return db.query(MedicalCondition).order_by(MedicalCondition.name).all()


@router.get("/allergens", response_model=list[ItemOut])
def allergens(db: Session = Depends(get_db)):
    return db.query(Allergen).order_by(Allergen.name).all()