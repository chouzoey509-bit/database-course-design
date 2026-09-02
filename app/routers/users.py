from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.models import User
from app.auth import get_current_user, CurrentUser, hash_password, verify_password

router = APIRouter()


class UpdateProfileRequest(BaseModel):
    real_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.get("/me")
def get_profile(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "user_id": user.user_id,
        "username": user.username,
        "real_name": user.real_name,
        "phone": user.phone,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "success_trade_count": user.success_trade_count,
        "created_at": user.created_at,
    }


@router.put("/me")
def update_profile(
    req: UpdateProfileRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.user_id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if req.real_name is not None:
        user.real_name = req.real_name
    if req.phone is not None:
        user.phone = req.phone
    if req.email is not None:
        user.email = req.email

    db.commit()
    return {"message": "个人信息已更新"}


@router.put("/me/password")
def change_password(
    req: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.user_id == current_user.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")

    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"message": "密码已修改"}
