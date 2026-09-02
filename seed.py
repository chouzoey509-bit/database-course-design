"""
运行方式：python seed.py
启动后端前，先在 MySQL 建好数据库（CREATE DATABASE campus_secondhand），
表会由应用自动创建；然后运行此脚本插入测试数据。
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, engine, Base
from app.models.models import User, Category, Item
from app.auth import hash_password

# 确保表已创建
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 管理员
admin = User(
    username="admin",
    password_hash=hash_password("admin123"),
    real_name="系统管理员",
    phone="13900000000",
    email="admin@campus.edu",
    role="ADMIN",
    status="ACTIVE",
)
# 普通用户
user1 = User(
    username="zhangsan",
    password_hash=hash_password("123456"),
    real_name="张三",
    phone="13811111111",
    email="zhangsan@campus.edu",
    role="USER",
    status="ACTIVE",
)
user2 = User(
    username="lisi",
    password_hash=hash_password("123456"),
    real_name="李四",
    phone="13822222222",
    email="lisi@campus.edu",
    role="USER",
    status="ACTIVE",
)

db.add_all([admin, user1, user2])
db.commit()

# 类别
books = Category(category_name="教材书籍", sort_order=1)
electronics = Category(category_name="电子产品", sort_order=2)
life = Category(category_name="生活用品", sort_order=3)
db.add_all([books, electronics, life])
db.commit()

# 子类别
db.add_all([
    Category(category_name="理工类教材", parent_id=books.category_id, sort_order=1),
    Category(category_name="文史类教材", parent_id=books.category_id, sort_order=2),
    Category(category_name="手机平板", parent_id=electronics.category_id, sort_order=1),
    Category(category_name="电脑配件", parent_id=electronics.category_id, sort_order=2),
])
db.commit()

# 示例物品
items = [
    Item(owner_id=user1.user_id, category_id=books.category_id,
         item_name="高等数学（第七版）上下册", original_price=69.0, discount=5.0, sale_price=34.5,
         description="九成新，无笔记，送配套习题册。", status="PUBLISHING"),
    Item(owner_id=user1.user_id, category_id=electronics.category_id,
         item_name="iPad Air 4 256G 键盘套装", original_price=5299.0, discount=7.0, sale_price=3709.3,
         description="使用一年，屏幕无划痕，附原装充电器。", status="PUBLISHING"),
    Item(owner_id=user2.user_id, category_id=life.category_id,
         item_name="宿舍台灯（护眼）", original_price=89.0, discount=6.0, sale_price=53.4,
         description="毕业用不上了，成色很好。", status="PUBLISHING"),
    Item(owner_id=user2.user_id, category_id=books.category_id,
         item_name="大学英语四级真题全套", original_price=35.0, discount=4.0, sale_price=14.0,
         description="2021-2023年合订本，有少量荧光笔标注。", status="PUBLISHING"),
]
db.add_all(items)
db.commit()

print("✅ 测试数据插入完成")
print("   管理员账号: admin / admin123")
print("   普通用户:   zhangsan / 123456")
print("   普通用户:   lisi / 123456")
db.close()
