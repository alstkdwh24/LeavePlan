import logging
from asyncio import log

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from models.planItem import PlanItem

# prefix="/api" -> 이 라우터의 모든 경로 앞에 /api가 붙음
router = APIRouter(prefix="/api", tags=["plan"])


@router.post("/plan")
def create_plan():
    print("안녕")
    logging.debug("create_plan")
    """여행 일정 생성 - 실제 경로: POST /api/plan"""
    return {"message": "Plan endpoint"}


@router.get("/plans")
def get_plans(db: Session = Depends(get_db)):
    return db.query(PlanItem).all()
