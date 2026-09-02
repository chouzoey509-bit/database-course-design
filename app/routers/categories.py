from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.models import Category
from app.auth import require_admin, CurrentUser

router = APIRouter()


class CategoryRequest(BaseModel):
    category_name: str
    parent_id: Optional[int] = None
    sort_order: int = 0


def cat_to_dict(c: Category):
    return {
        "category_id": c.category_id,
        "category_name": c.category_name,
        "parent_id": c.parent_id,
        "sort_order": c.sort_order,
        "status": c.status,
        "children": [cat_to_dict(child) for child in c.children if child.status == "ACTIVE"],
    }


@router.get("")
def list_categories(db: Session = Depends(get_db)):
    top_level = (
        db.query(Category)
        .filter(Category.parent_id == None, Category.status == "ACTIVE")
        .order_by(Category.sort_order)
        .all()
    )
    return [cat_to_dict(c) for c in top_level]


@router.post("")
def create_category(
    req: CategoryRequest,
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cat = Category(
        category_name=req.category_name,
        parent_id=req.parent_id,
        sort_order=req.sort_order,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"message": "类别已创建", "category_id": cat.category_id}


@router.put("/{category_id}")
def update_category(
    category_id: int,
    req: CategoryRequest,
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cat = db.query(Category).filter(Category.category_id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")

    cat.category_name = req.category_name
    cat.parent_id = req.parent_id
    cat.sort_order = req.sort_order
    db.commit()
    return {"message": "类别已更新"}


@router.delete("/{category_id}")
def disable_category(
    category_id: int,
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cat = db.query(Category).filter(Category.category_id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="类别不存在")

    cat.status = "DISABLED"
    db.commit()
    return {"message": "类别已禁用"}
