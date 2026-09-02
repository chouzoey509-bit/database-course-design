from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.models import User
from app.auth import hash_password, verify_password, create_access_token, get_current_user, CurrentUser

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str
    password: str
    real_name: Optional[str] = None
    phone: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        real_name=req.real_name,
        phone=req.phone,
        email=req.email,
        role="USER",
        status="ACTIVE",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "注册成功", "user_id": user.user_id}


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    token = create_access_token({
        "sub": str(user.user_id),
        "username": user.username,
        "role": user.role,
        "status": user.status,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "real_name": user.real_name,
            "role": user.role,
        }
    }


@router.get("/me")
def me(current_user: CurrentUser = Depends(get_current_user)):
    return current_user
