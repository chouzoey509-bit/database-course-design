from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from app.database import get_db
from app.models.models import Item, SearchLog, ItemArchive, User
from app.auth import (
    get_current_user,
    get_current_user_optional,
    CurrentUser,
    ensure_item_owner_or_admin,
)

router = APIRouter()


class PublishItemRequest(BaseModel):
    category_id: int
    item_name: str
    original_price: float
    discount: float
    sale_price: Optional[float] = None
    description: Optional[str] = None
    primary_image_url: Optional[str] = None


class UpdateItemRequest(BaseModel):
    item_name: Optional[str] = None
    category_id: Optional[int] = None
    original_price: Optional[float] = None
    discount: Optional[float] = None
    sale_price: Optional[float] = None
    description: Optional[str] = None
    primary_image_url: Optional[str] = None


def item_to_dict(item: Item):
    return {
        "item_id": item.item_id,
        "owner_id": item.owner_id,
        "owner_name": item.owner.username if item.owner else None,
        "owner_phone": item.owner.phone if item.owner else None,
        "category_id": item.category_id,
        "category_name": item.category.category_name if item.category else None,
        "item_name": item.item_name,
        "original_price": float(item.original_price),
        "discount": float(item.discount),
        "sale_price": float(item.sale_price),
        "description": item.description,
        "status": item.status,
        "view_count": item.view_count,
        "primary_image_url": item.primary_image_url,
        "created_at": item.created_at,
        "ended_at": item.ended_at,
    }


def _calc_sale_price(original_price: float, discount: float) -> float:
    """折扣为“几折”，例如 8.5 表示八五折。售价 = 原价 * 折扣 / 10。"""
    return round(float(original_price) * float(discount) / 10, 2)


@router.get("")
def list_items(
    keyword: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query("PUBLISHING"),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    query = db.query(Item)

    if status:
        query = query.filter(Item.status == status)
    if keyword:
        query = query.filter(
            or_(Item.item_name.contains(keyword), Item.description.contains(keyword))
        )
    if category_id:
        query = query.filter(Item.category_id == category_id)
    if min_price is not None:
        query = query.filter(Item.sale_price >= min_price)
    if max_price is not None:
        query = query.filter(Item.sale_price <= max_price)

    total = query.count()
    items = query.order_by(Item.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # 记录搜索日志（尽力而为，失败不影响主流程）
    try:
        if keyword or category_id:
            log = SearchLog(
                user_id=current_user.user_id if current_user else None,
                keyword=keyword,
                category_id=category_id,
            )
            db.add(log)
            db.commit()
    except Exception:
        db.rollback()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [item_to_dict(i) for i in items],
    }


# 注意：/mine 必须声明在 /{item_id} 之前，否则会被当成 item_id 解析
@router.get("/mine")
def list_my_items(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Item).filter(Item.owner_id == current_user.user_id)
    if status:
        query = query.filter(Item.status == status)

    total = query.count()
    items = query.order_by(Item.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [item_to_dict(i) for i in items],
    }


@router.get("/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")

    # 浏览量 +1
    item.view_count += 1
    db.commit()

    return item_to_dict(item)


@router.post("")
def publish_item(
    req: PublishItemRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (0 < req.discount <= 10):
        raise HTTPException(status_code=400, detail="折扣必须在 0 到 10 之间（几折）")
    if req.original_price <= 0:
        raise HTTPException(status_code=400, detail="原价必须大于 0")

    # 售价以服务端按折扣重新计算为准，避免前端传错
    sale_price = _calc_sale_price(req.original_price, req.discount)

    item = Item(
        owner_id=current_user.user_id,
        category_id=req.category_id,
        item_name=req.item_name,
        original_price=req.original_price,
        discount=req.discount,
        sale_price=sale_price,
        description=req.description,
        primary_image_url=req.primary_image_url,
        status="PUBLISHING",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"message": "物品发布成功", "item_id": item.item_id}


@router.put("/{item_id}")
def update_item(
    item_id: int,
    req: UpdateItemRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")

    ensure_item_owner_or_admin(item, current_user)

    if item.status != "PUBLISHING":
        raise HTTPException(status_code=400, detail="只有发布中的物品可以修改")

    data = req.model_dump(exclude_none=True)
    if "discount" in data and not (0 < data["discount"] <= 10):
        raise HTTPException(status_code=400, detail="折扣必须在 0 到 10 之间（几折）")

    for field, value in data.items():
        setattr(item, field, value)

    # 原价或折扣变化时重新计算售价
    if "original_price" in data or "discount" in data:
        item.sale_price = _calc_sale_price(item.original_price, item.discount)

    db.commit()
    return {"message": "物品信息已更新"}


@router.put("/{item_id}/end")
def end_item(
    item_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")

    # 仅物主本人可结束自己发布的物品（交易完成）
    if item.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="只能结束自己发布的物品")

    if item.status != "PUBLISHING":
        raise HTTPException(status_code=400, detail="只有发布中的物品可以结束发布")

    now = datetime.now(timezone.utc)
    item.status = "ENDED"
    item.ended_at = now

    # 归档记录
    archive = ItemArchive(
        item_id=item.item_id,
        owner_id=item.owner_id,
        category_id=item.category_id,
        item_name=item.item_name,
        original_price=item.original_price,
        discount=item.discount,
        sale_price=item.sale_price,
        description=item.description,
        published_at=item.created_at,
        ended_at=now,
    )
    db.add(archive)

    # 成功交易次数 +1
    owner = db.query(User).filter(User.user_id == item.owner_id).first()
    if owner:
        owner.success_trade_count += 1

    db.commit()
    return {"message": "物品发布已结束，交易完成"}


@router.delete("/{item_id}")
def delete_item(
    item_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")

    ensure_item_owner_or_admin(item, current_user)

    if item.status == "PUBLISHING":
        raise HTTPException(status_code=400, detail="发布中的物品不能直接删除，请先结束发布")

    db.delete(item)
    db.commit()
    return {"message": "物品已删除"}
