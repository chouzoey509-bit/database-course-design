import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import auth, users, items, categories, admin, upload
from app.database import engine, Base

# 自动建表（表不存在时创建；已存在则不改动）
Base.metadata.create_all(bind=engine)

app = FastAPI(title="校园二手物品平台 API", version="1.0.0")

# 本接口使用 Bearer Token（放在 Authorization 头），不依赖 Cookie，
# 因此 allow_credentials 设为 False，配合 "*" 才能被浏览器接受。
# 若将来要用 Cookie，请把 allow_origins 改成具体域名并将 credentials 设为 True。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态资源：用户上传的图片
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.getcwd(), "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(items.router, prefix="/api/items", tags=["物品"])
app.include_router(categories.router, prefix="/api/categories", tags=["类别"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理员"])
app.include_router(upload.router, prefix="/api/upload", tags=["上传"])


@app.get("/")
def root():
    return {"message": "校园二手物品平台 API 运行正常"}
