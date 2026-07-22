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
- Bearer JWT 单 Token；修改密码时递增用户令牌版本，使旧令牌立即失效；MVP 不实现 Refresh Token。
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

- 建表方式：Alembic。
- 事务边界：每个创建、上传、移动、复制、删除、恢复或分享操作独立事务。

## 5. API 约定

- 前缀：`/api/v1`
- 认证：`Authorization: Bearer <JWT>`
- 分页：`items / total / page / page_size`
- 错误：`code / message / details`
- 创建返回 201，删除返回 204；401/403/404/409/422 保持语义。

主要资源：`/auth`、`/nodes`、`/trash`、`/shares`、`/public/shares`、`/storage`。OpenAPI `/docs` 是字段级事实来源。

## 6. 权限与文件

- 所有私有节点查询同时限定 `owner_id` 与当前状态，越权不泄露归属。
- 分享访问只允许分享节点或文件夹后代，且每次检查到期、撤销和源节点状态。
- 文件名需通过业务校验；同级名称不区分大小写判重。
- 默认单文件上限 1 GiB、用户总容量 5 GiB。
- 实际文件保存在 `STORAGE_PATH`；下载文件名使用业务名称，磁盘路径永不使用用户输入。

## 7. 配置

| 环境变量 | 用途 | 必填 | 安全示例 |
| --- | --- | --- | --- |
| DATABASE_URL | 异步 PostgreSQL DSN | 是 | `postgresql+asyncpg://pan:pan@db:5432/pan` |
| SECRET_KEY | JWT 签名 | 是 | 本地开发示例值，生产必须替换 |
| STORAGE_PATH | 持久化目录 | 是 | `/data/files` |
| CORS_ORIGINS | 前端来源 | 是 | `http://localhost:8080` |
| DEFAULT_QUOTA_BYTES | 默认容量 | 否 | `5368709120` |
| MAX_FILE_SIZE_BYTES | 单文件上限 | 否 | `1073741824` |

## 8. Docker 与验证

- Compose：`docker-compose.yml`
- 应用：`http://localhost:8080`
- API 健康检查：`http://localhost:8000/health`
- 持久化位置：PostgreSQL 使用 `postgres_data` 数据卷；上传文件绑定到项目目录 `data/files`。
- 存储分片：每天按 UUID 前两位分为 256 个目录；旧版平铺键在应用启动时执行可恢复迁移。
- 国内镜像：DaoCloud Docker Hub 代理、npmmirror、清华 pip 镜像。
- 测试：`pytest`；迁移：`alembic upgrade head`。

## 9. 非目标

- 多实例并行写文件、断点续传、内容去重、病毒扫描与后台清理 Worker。
- 这些能力需要时再引入对象存储、上传会话和独立任务进程。
