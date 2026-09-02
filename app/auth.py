import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User

SECRET_KEY = os.getenv("SECRET_KEY", "campus-secondhand-secret-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
# auto_error=False -> 接口可选登录（游客也能访问）时使用，未带 token 不会直接抛 401
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"


class CurrentUser(BaseModel):
    user_id: int
    username: str
    role: UserRole
    status: str


def hash_password(password: str) -> str:
    # bcrypt 只处理前 72 字节，超出部分截断，避免 backend 抛异常
    return pwd_context.hash(password[:72])


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def _load_current_user(token: str, db: Session) -> CurrentUser:
    """解析 token 并从数据库读取最新用户信息（角色/状态以数据库为准）。"""
    try:
        payload = _decode_token(token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="无效的认证信息")

    user = db.query(User).filter(User.user_id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")

    # 关键：状态以数据库实时为准，管理员封禁后立即生效
    if user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="账号已被禁用")

    return CurrentUser(
        user_id=user.user_id,
        username=user.username,
        role=UserRole(user.role),
        status=user.status,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    return _load_current_user(token, db)


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> Optional[CurrentUser]:
    """登录可选：带了有效 token 就返回用户，否则返回 None（游客）。"""
    if not token:
        return None
    try:
        return _load_current_user(token, db)
    except HTTPException:
        return None


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="仅系统管理员可执行该操作")
    return current_user


def ensure_item_owner_or_admin(item, current_user: CurrentUser):
    if current_user.role == UserRole.ADMIN:
        return
    if item.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="无权操作该物品")
