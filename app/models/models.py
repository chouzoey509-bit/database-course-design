from sqlalchemy import (
    Column, BigInteger, String, Text, Boolean,
    Integer, DateTime, ForeignKey, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(50))
    phone = Column(String(20), nullable=False)
    email = Column(String(100))
    role = Column(String(20), nullable=False, default="USER")
    status = Column(String(20), nullable=False, default="ACTIVE")
    success_trade_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    items = relationship("Item", back_populates="owner", foreign_keys="Item.owner_id")
    search_logs = relationship("SearchLog", back_populates="user")
    admin_logs = relationship("AdminLog", back_populates="admin")


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(BigInteger, primary_key=True, autoincrement=True)
    category_name = Column(String(50), nullable=False)
    parent_id = Column(BigInteger, ForeignKey("categories.category_id", ondelete="SET NULL"))
    sort_order = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="ACTIVE")

    # 自关联（邻接表）：children 为一对多，parent 为多对一，二者用 back_populates 关联，
    # remote_side 指向主键，SQLAlchemy 即可自动识别外键，不再产生 overlaps 警告/报错。
    children = relationship(
        "Category",
        back_populates="parent",
    )
    parent = relationship(
        "Category",
        back_populates="children",
        remote_side=[category_id],
    )
    items = relationship("Item", back_populates="category")


class Item(Base):
    __tablename__ = "items"

    item_id = Column(BigInteger, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    category_id = Column(BigInteger, ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False)
    item_name = Column(String(100), nullable=False)
    original_price = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(4, 2), nullable=False)
    sale_price = Column(Numeric(10, 2), nullable=False)
    description = Column(Text)
    status = Column(String(20), nullable=False, default="PUBLISHING")
    view_count = Column(Integer, nullable=False, default=0)
    primary_image_url = Column(String(500))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    ended_at = Column(DateTime)

    owner = relationship("User", back_populates="items", foreign_keys=[owner_id])
    category = relationship("Category", back_populates="items")
    images = relationship("ItemImage", back_populates="item", cascade="all, delete-orphan")


class ItemImage(Base):
    __tablename__ = "item_images"

    image_id = Column(BigInteger, primary_key=True, autoincrement=True)
    item_id = Column(BigInteger, ForeignKey("items.item_id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String(500), nullable=False)
    is_primary = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    item = relationship("Item", back_populates="images")


class ItemArchive(Base):
    __tablename__ = "item_archive"

    archive_id = Column(BigInteger, primary_key=True, autoincrement=True)
    item_id = Column(BigInteger, ForeignKey("items.item_id", ondelete="RESTRICT"), nullable=False, unique=True)
    owner_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    category_id = Column(BigInteger, ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=False)
    item_name = Column(String(100), nullable=False)
    original_price = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(4, 2), nullable=False)
    sale_price = Column(Numeric(10, 2), nullable=False)
    description = Column(Text)
    published_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)
    archived_at = Column(DateTime, nullable=False, server_default=func.now())


class SearchLog(Base):
    __tablename__ = "search_logs"

    search_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"))
    keyword = Column(String(100))
    category_id = Column(BigInteger, ForeignKey("categories.category_id", ondelete="SET NULL"))
    searched_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="search_logs")


class AdminLog(Base):
    __tablename__ = "admin_logs"

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    admin_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    action_type = Column(String(50), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(BigInteger, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    admin = relationship("User", back_populates="admin_logs")
