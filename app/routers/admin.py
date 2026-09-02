from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.models import User, Item, AdminLog, SearchLog
from app.auth import require_admin, CurrentUser

router = APIRouter()


def write_log(db, admin_id, action_type, target_type, target_id, description):
    log = AdminLog(
        admin_id=admin_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        description=description,
    )
    db.add(log)


# ── Users ──────────────────────────────────────────────

@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "users": [
            {
                "user_id": u.user_id,
                "username": u.username,
                "real_name": u.real_name,
                "phone": u.phone,
                "email": u.email,
                "role": u.role,
                "status": u.status,
                "success_trade_count": u.success_trade_count,
                "created_at": u.created_at,
            }
            for u in users
        ],
    }


class UpdateStatusRequest(BaseModel):
    status: str


@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    req: UpdateStatusRequest,
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if req.status not in ("ACTIVE", "DISABLED"):
        raise HTTPException(status_code=400, detail="状态值无效")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="不能修改自己的状态")

    old_status = user.status
    user.status = req.status

    action = "DISABLE_USER" if req.status == "DISABLED" else "ENABLE_USER"
    write_log(db, admin.user_id, action, "USER", user_id,
              f"将用户 {user.username} 状态从 {old_status} 改为 {req.status}")

    db.commit()
    return {"message": f"用户状态已更新为 {req.status}"}


# ── Items ──────────────────────────────────────────────

@router.get("/items")
def admin_list_items(
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Item)
    if status:
        query = query.filter(Item.status == status)
    if keyword:
        query = query.filter(Item.item_name.contains(keyword))

    total = query.count()
    items = query.order_by(Item.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "items": [
            {
                "item_id": i.item_id,
                "item_name": i.item_name,
                "owner_id": i.owner_id,
                "owner_name": i.owner.username if i.owner else None,
                "category_id": i.category_id,
                "sale_price": float(i.sale_price),
                "status": i.status,
                "view_count": i.view_count,
                "created_at": i.created_at,
            }
            for i in items
        ],
    }


class TakeDownRequest(BaseModel):
    reason: Optional[str] = None


@router.put("/items/{item_id}/take-down")
def take_down_item(
    item_id: int,
    req: TakeDownRequest = TakeDownRequest(),
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")

    if item.status == "REMOVED":
        raise HTTPException(status_code=400, detail="物品已下架")

    item.status = "REMOVED"
    write_log(db, admin.user_id, "TAKE_DOWN_ITEM", "ITEM", item_id,
              f"下架物品《{item.item_name}》，原因：{req.reason or '违规'}")

    db.commit()
    return {"message": "违规物品已下架"}


# ── Logs ──────────────────────────────────────────────

@router.get("/logs")
def get_admin_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(AdminLog).order_by(AdminLog.created_at.desc())
    total = query.count()
    logs = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "logs": [
            {
                "log_id": l.log_id,
                "admin_id": l.admin_id,
                "admin_name": l.admin.username if l.admin else None,
                "action_type": l.action_type,
                "target_type": l.target_type,
                "target_id": l.target_id,
                "description": l.description,
                "created_at": l.created_at,
            }
            for l in logs
        ],
    }


@router.get("/search-logs")
def get_search_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(SearchLog).order_by(SearchLog.searched_at.desc())
    total = query.count()
    logs = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "logs": [
            {
                "search_id": l.search_id,
                "user_id": l.user_id,
                "keyword": l.keyword,
                "category_id": l.category_id,
                "searched_at": l.searched_at,
            }
            for l in logs
        ],
    }
