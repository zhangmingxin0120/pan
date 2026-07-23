# BACKEND

## 1. 概况

- 服务名称：Pan API
- 业务范围：认证、个人文件空间、文件操作、回收站和只读分享
- Python / FastAPI：Python 3.12 / FastAPI 0.115
- 数据库：PostgreSQL 16，SQLAlchemy 2 异步访问
- 部署方式：Docker Compose；文件存储使用项目目录 bind mount，数据库使用持久化卷

## 2. 简化决策

- 采用按模块拆分结构：`api/v1`、`core`、`models`、`schemas`、`services`。
- 不引入 Repository、Unit of Work、Redis、Celery、微服务、对象存储和通用响应包装。
- 网页用户使用 HttpOnly Cookie 承载 JWT，会话写操作同时校验同源请求与绑定用户/令牌版本的签名 CSRF Token；外部系统使用独立高熵 API Key，数据库只保存 HMAC-SHA256 摘要。
- 真实文件使用 `YYYY/MM/DD/{UUID前2位}/{完整UUID}` 存储键（UTC 日期），业务名称与虚拟路径仅保存在数据库。

## 3. 目录与职责

| 目录 / 文件 | 职责 |
| --- | --- |
| `app/api/v1` | HTTP 路由、依赖与状态码 |
| `app/core` | 配置、数据库、安全与错误 |
| `app/models` | SQLAlchemy 数据模型 |
| `app/schemas` | Pydantic 输入输出 |
| `app/services` | 文件树、存储、容量、复制与恢复事务 |
| `alembic` | PostgreSQL 迁移 |

## 4. 数据模型

| 实体 | 关键字段 | 约束 / 索引 | 关系 |
| --- | --- | --- | --- |
| users | email、name、password_hash、quota_bytes | email 大小写不敏感唯一 | 拥有 nodes/shares |
| nodes | owner_id、parent_id、kind、name、size、storage_key、trashed_at | owner/parent/lower(name) 活跃唯一；父级索引 | 自引用目录树 |
| shares | owner_id、node_id、token、expires_at、revoked_at | token 唯一 | 指向 node |
| api_applications | user_id、key_prefix、key_hash、权限与累计用量 | key_prefix 唯一 | 指向绑定用户 |

- 建表方式：Alembic。
- 事务边界：每个创建、上传、移动、复制、删除、恢复或分享操作独立事务。

## 5. API 约定

- 前缀：`/api/v1`
- 认证：网页用户接口使用 HttpOnly Cookie；受信任的非浏览器客户端仍可使用 `Authorization: Bearer <JWT>`；`/open` 使用独立 API Key
- 分页：`items / total / page / page_size`
- 错误：`code / message / details`
- 创建返回 201，删除返回 204；401/403/404/409/422 保持语义。

主要资源：`/auth`、`/nodes`、`/trash`、`/shares`、`/public/shares`、`/storage`、`/open`。外部接口以产品化文档手册 `/api-docs` 为事实来源，生产服务不公开内部 Swagger 清单。

## 6. 权限与文件

- 所有私有节点查询同时限定 `owner_id` 与当前状态，越权不泄露归属。
- 登录响应不向 JavaScript 暴露 JWT；Cookie 请求的非安全方法必须通过签名 CSRF Token 与 Origin 校验。
- 分享访问只允许分享节点或文件夹后代，且每次检查到期、撤销和源节点状态。
- API 应用只允许访问绑定账号的资源，并独立检查读取列表/详情、下载、上传、目录与名称管理、删除到回收站五项权限；轮换或停用后旧密钥立即失效。
- 文件名需通过业务校验；同级名称不区分大小写判重。
- 默认单文件上限 1 GiB、用户总容量 5 GiB。
- 实际文件保存在 `STORAGE_PATH`；下载文件名使用业务名称，磁盘路径永不使用用户输入。

## 7. 配置

| 环境变量 | 用途 | 必填 | 安全示例 |
| --- | --- | --- | --- |
| DATABASE_URL | 异步 PostgreSQL DSN | 是 | `postgresql+asyncpg://pan:pan@db:5432/pan` |
| SECRET_KEY | JWT 签名 | 是 | 本地开发示例值，生产必须替换 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Cookie 会话有效期 | 否 | `10080`（7 天） |
| COOKIE_SECURE | 仅允许 HTTPS 发送会话 Cookie | 生产必填 | HTTPS 部署为 `true` |
| COOKIE_SAMESITE | Cookie 跨站策略 | 否 | `lax` |
| STORAGE_PATH | 持久化目录 | 是 | `/data/files` |
| CORS_ORIGINS | 允许携带 Cookie 的准确前端来源 | 是 | `http://localhost:8091`，禁止 `*` |
| DEFAULT_QUOTA_BYTES | 默认容量 | 否 | `5368709120` |
| MAX_FILE_SIZE_BYTES | 单文件上限 | 否 | `1073741824` |

## 8. Docker 与验证

- Compose：`docker-compose.yml`
- 应用：`http://localhost:8091`
- API 健康检查：`http://localhost:8092/health`
- 持久化位置：PostgreSQL 使用 `postgres_data` 数据卷；上传文件绑定到项目目录 `data/files`。
- 存储分片：每天按 UUID 前两位分为 256 个目录；旧版平铺键在应用启动时执行可恢复迁移。
- 国内镜像：DaoCloud Docker Hub 代理、npmmirror、清华 pip 镜像。
- 测试：`pytest`；迁移：`alembic upgrade head`。

## 9. 非目标

- 多实例并行写文件、断点续传、内容去重、病毒扫描与后台清理 Worker。
- 这些能力需要时再引入对象存储、上传会话和独立任务进程。
