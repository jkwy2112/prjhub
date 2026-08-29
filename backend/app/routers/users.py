from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserOut], summary="用户列表(添加成员时搜索)")
def list_users(q: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(User).filter(User.is_active.is_(True))
    if q:
        like = f"%{q}%"
        query = query.filter(User.username.like(like) | User.name.like(like) | User.email.like(like))
    return query.order_by(User.id).limit(50).all()
