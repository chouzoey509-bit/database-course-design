# 校园二手物品平台（拾光）

FastAPI + MySQL 后端 + 单文件前端（`index.html`）。本版本修复了登录注册问题、补全了**发布物品 / 图片上传 / 物主结束发布（成交）** 等功能，并实现了**管理员 / 普通用户的分级权限**。

---

## 一、本次修复与新增清单

### 后端 Bug 修复
1. **`app/routers/items.py` 可选登录失效**：原代码 `Depends(lambda: None)` 永远返回 `None`，导致搜索日志无法记录登录用户。已改为真正的可选鉴权依赖 `get_current_user_optional`。
2. **`app/auth.py` 权限不实时**：原 `get_current_user` 只读取 token 里的角色/状态，管理员封禁用户或改角色后，旧 token 在 24 小时内仍然有效。已改为**每次请求都从数据库读取最新用户**，封禁/改角色立即生效（这是分级权限可靠的关键）。
3. **`app/models/models.py` 分类自关联报错**：`Category` 的 `parent` / `children` 共用同一外键却未协调，SQLAlchemy 2.0 会报 overlaps 警告/错误。已用 `back_populates` + `remote_side` 正确配置。
4. **`requirements.txt` bcrypt 不兼容**：未锁定 bcrypt 版本时会装上 4.1+，而 `passlib 1.7.4` 读取其 `__about__` 失败，日志报错、部分环境密码哈希异常。已锁定 **`bcrypt==4.0.1`**。
5. **`main.py` CORS 配置浏览器拒绝**：`allow_origins=["*"]` 与 `allow_credentials=True` 同时存在会被浏览器拦截（前后端分离时登录失败的常见原因）。本接口用 Bearer Token 不依赖 Cookie，已将 `allow_credentials` 改为 `False`。
6. **`app/routers/auth.py` 多余依赖**：导入了未使用的 `EmailStr`（需要额外的 `email-validator`），已移除。
7. **`runtime.txt`**：`python-3.11` 不是合法部署版本号，已改为 `python-3.11.9`。
8. 价格相关：发布/修改时**售价由后端按折扣自动计算**（售价 = 原价 × 折扣 ÷ 10），避免前端传错。

### 后端新增
- **`POST /api/upload/image`**：图片上传接口，保存到 `uploads/` 并由 `/uploads/...` 静态访问。
- **`GET /api/items/mine`**：查询“我发布的物品”（含各状态），供“我的发布”页使用。

### 前端（全新 `index.html`）
> 原上传的 `index__3_.html` 未能成功传入，故重建了一个完整可用的单文件前端。

- 登录 / 注册（含接口地址配置，token 本地保存、刷新不掉登录）
- 市场浏览：关键词 / 分类 / 价格区间筛选，物品详情含**卖家联系方式**
- **发布物品**：表单 + **图片上传** + 折后价实时计算
- **我的发布**：编辑、删除，以及**「结束发布（已成交）」**
- 个人中心：修改资料、修改密码
- **管理后台（仅管理员可见）**：用户启禁用、物品下架、分类增改禁、操作日志、搜索日志

---

## 二、运行步骤

### 1. 准备数据库（MySQL）
只需创建空库，表会自动创建：
```sql
CREATE DATABASE campus_secondhand DEFAULT CHARACTER SET utf8mb4;
```

### 2. 配置连接（可选）
默认连接 `mysql+pymysql://root:password@localhost:3306/campus_secondhand`，如不同请设置环境变量：
```bash
export DATABASE_URL="mysql+pymysql://用户名:密码@主机:3306/campus_secondhand?charset=utf8mb4"
export SECRET_KEY="换成你自己的随机密钥"
```

### 3. 安装依赖并启动后端
```bash
pip install -r requirements.txt
python seed.py          # 插入测试数据（管理员、普通用户、分类、示例物品）
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
接口文档：`http://localhost:8000/docs`

### 4. 打开前端
直接用浏览器打开 `index.html` 即可（建议用本地静态服务器以避免个别浏览器限制）：
```bash
python -m http.server 5500   # 然后访问 http://localhost:5500/index.html
```
若后端不在 `http://localhost:8000`，在登录页底部「⚙ 后端接口地址设置」里填写你的后端地址。

### 测试账号
| 角色 | 用户名 | 密码 |
|---|---|---|
| 管理员 | `admin` | `admin123` |
| 普通用户 | `zhangsan` | `123456` |
| 普通用户 | `lisi` | `123456` |

---

## 三、角色权限对照

| 功能 | 普通用户 | 管理员 |
|---|:--:|:--:|
| 浏览 / 搜索物品、查看卖家 | ✅ | ✅ |
| 发布物品、上传图片 | ✅ | ✅ |
| 编辑 / 删除自己的物品 | ✅ | ✅（含他人物品） |
| 结束自己物品的发布（成交） | ✅ | — |
| 修改本人资料 / 密码 | ✅ | ✅ |
| 启用 / 禁用用户 | ❌ | ✅ |
| 下架违规物品 | ❌ | ✅ |
| 管理分类（增 / 改 / 禁） | ❌ | ✅ |
| 查看操作日志 / 搜索日志 | ❌ | ✅ |

权限同时在**后端强制校验**（`require_admin` / 物主校验）与**前端按角色显隐**，双重保障。

---

## 四、说明
- 上传图片保存在服务器本地 `uploads/` 目录。若部署到 Heroku 等**临时文件系统**平台，重启后文件会丢失，生产环境建议改用对象存储（OSS / S3）。
- 物品状态：`PUBLISHING` 在售 → `ENDED` 已成交（物主结束）/ `REMOVED` 已下架（管理员）。
