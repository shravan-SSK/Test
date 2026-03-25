from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from database import get_db
from models import SalesCycle, Activity
from schemas import SalesCycleCreate, SalesCycleUpdate, SalesCycleOut, ActivityOut, StageAdvanceRequest

router = APIRouter(prefix="/sales-cycle", tags=["Sales Cycle"])


@router.get("/pipeline", response_model=Dict)
def get_pipeline(db: Session = Depends(get_db)):
    """Full pipeline summary – counts and values by stage."""
    from services.sales_cycle_manager import get_pipeline_summary
    return get_pipeline_summary(db)


@router.get("/", response_model=List[SalesCycleOut])
def list_cycles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(SalesCycle).offset(skip).limit(limit).all()


@router.get("/{cycle_id}", response_model=SalesCycleOut)
def get_cycle(cycle_id: int, db: Session = Depends(get_db)):
    cycle = db.query(SalesCycle).filter(SalesCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(404, "Sales cycle not found")
    return cycle


@router.put("/{cycle_id}", response_model=SalesCycleOut)
def update_cycle(cycle_id: int, payload: SalesCycleUpdate, db: Session = Depends(get_db)):
    cycle = db.query(SalesCycle).filter(SalesCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(404, "Sales cycle not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(cycle, k, v)
    db.commit()
    db.refresh(cycle)
    return cycle


@router.post("/{cycle_id}/advance", response_model=Dict)
def advance(cycle_id: int, req: StageAdvanceRequest, db: Session = Depends(get_db)):
    """Move a deal to a new stage."""
    from services.sales_cycle_manager import advance_stage
    try:
        cycle, message = advance_stage(db, cycle_id, req.new_stage, req.notes)
        db.commit()
        db.refresh(cycle)
        return {"cycle": SalesCycleOut.model_validate(cycle), "message": message}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/{cycle_id}/activities", response_model=List[ActivityOut])
def get_activities(cycle_id: int, db: Session = Depends(get_db)):
    activities = (
        db.query(Activity)
        .filter(Activity.sales_cycle_id == cycle_id)
        .order_by(Activity.created_at.desc())
        .all()
    )
    return activities


@router.post("/{cycle_id}/activities", response_model=ActivityOut, status_code=201)
def log_activity(cycle_id: int, title: str, description: str = "",
                 act_type: str = "note", db: Session = Depends(get_db)):
    cycle = db.query(SalesCycle).filter(SalesCycle.id == cycle_id).first()
    if not cycle:
        raise HTTPException(404, "Sales cycle not found")
    act = Activity(
        sales_cycle_id=cycle_id,
        type=act_type,
        title=title,
        description=description,
    )
    db.add(act)
    db.commit()
    db.refresh(act)
    return act
