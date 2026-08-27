# 后端规格（FastAPI）

## 技术约束

- Python ≥ 3.12；依赖固定写在 `backend/requirements.txt`：
  `fastapi`、`uvicorn[standard]`、`sqlalchemy>=2.0`、`pydantic>=2`、`pydantic-settings`、`PyJWT`、`bcrypt`；测试用 `pytest`、`httpx`。
- 不使用 passlib（直接用 bcrypt）。TOML 解析用标准库 `tomllib`。
- SQLAlchemy 2.x 风格（`Mapped[]` / `mapped_column`），SQLite 开 WAL：`PRAGMA journal_mode=WAL`。
- 配置走环境变量（pydantic-settings），字段：
  - `SECRET_KEY`（默认 `dev-secret-change-me`，生产必须覆盖）
  - `APP_ENV`（`development | test | production`；本地 uvicorn 默认 development，后端镜像与 compose 默认 production）
  - `PUBLIC_ORIGIN`（生产站点的精确 HTTPS origin，用于 Origin 校验）
  - `DATABASE_URL`（默认 `sqlite:///data/leetpath.db`，相对 backend 目录；启动时自动建目录）
  - `TOKEN_TTL_DAYS`（默认 7）
  - `COOKIE_NAME`（默认 `leetpath_token`）
  - `COOKIE_SECURE`（默认 false）
- production 下 `SECRET_KEY` 必须至少 32 字节且不能使用开发默认值，`COOKIE_SECURE` 必须为 true，`PUBLIC_ORIGIN` 必须为 HTTPS，否则启动失败。
- 入口 `app/main.py`：挂所有 router（前缀 `/api`），启动时 `Base.metadata.create_all`。开发/测试启用配置的 CORS；production 关闭 CORS、OpenAPI 与文档，并对所有非安全方法校验精确 `Origin`。
- 除 `/api/auth/*` 外的所有接口要求登录（依赖注入解析 cookie 中的 JWT，失败 401）。

## 数据模型（`app/models.py`）

- `User`: id, username(唯一索引, 3-32), email(可空), password_hash, is_admin(bool, 默认 False), avatar_path(可空), avatar_updated_at(可空), token_version(int, 默认 0), created_at
- `Invite`: id, code_hash(SHA-256, 唯一), expires_at, used_at(可空), revoked_at(可空), created_by_id, used_by_id(可空), created_at
- `Problem`: id, slug(唯一索引), leetcode_id(可空, 力扣原题号), title, difficulty(`easy|medium|hard`), source(`hot100|mianjing`), tags(JSON list[str]), statement_md(Text), time_limit_ms(默认 5000), memory_limit_mb(默认 256), is_published(bool 默认 True), leetcode_spec(JSON, 可空, 力扣函数签名), created_at
- `Testcase`: id, problem_id(FK, 索引), ordinal(int), input(Text), expected_output(Text), is_sample(bool)；UniqueConstraint(problem_id, ordinal)
- `Submission`: id, user_id(FK, 索引), problem_id(FK), language(`python3|cpp`), io_mode(`acm|leetcode`, 默认 `acm`), code(Text), status(默认 `pending`, 索引), detail(JSON, 可空), compile_output(Text, 可空), runtime_ms(int, 可空), created_at(索引)
- `Draft`: 联合主键(user_id, problem_id, language)；code(Text), updated_at
- `Job`: id, company, position, batch(可空, 如 `2026秋招`), open_at(Date, 可空), deadline_at(Date, 可空, 索引), jd_text(Text, 可空), apply_url(可空), status(默认 `open`, 另有 `closed`), created_at
- `JobTrack`: 联合主键(user_id, job_id)，status(`applied|test|interview|offer|rejected`), updated_at；`none` 只作为清除记录的 API 输入值
- `QuizQuestion`: id, bank, category, type(`single|multiple|judge`), ordinal, stem, options(JSON), answer, analysis, created_at
- `QuizRecord`: 联合主键(user_id, question_id)，最后答案/对错、attempts_count、wrong_count、收藏、斩题与最后作答时间
- `QuizSolveEvent`: 联合主键(user_id, question_id)，记录首次答对时间

提交状态枚举：`pending | judging | AC | WA | TLE | MLE | CE | RE | IE`。

## 认证（`app/auth.py` + `app/routers/auth.py`）

- bcrypt 哈希；JWT（HS256，payload: sub=user_id, ver=token_version, exp）；登录成功写 HttpOnly Cookie（SameSite=Lax，secure 取 COOKIE_SECURE，path=/）。改密后 `token_version + 1` 并签发新 cookie，旧 cookie 失效。
- `POST /api/auth/register` body `{username, password, email?, invite_code}`：username 只允许 `[a-zA-Z0-9_]{3,32}`，password 为 8-72 UTF-8 字节。邀请码必须未使用、未撤销且未过期，并通过条件更新原子认领；失败 → 400。用户名已存在 → 409。注册用户一律 `is_admin=False`。每 IP 每小时最多 5 次尝试。
- 管理员通过 `python -m app.manage create-admin <username>` 初始化，不存在“首位注册自动管理员”。
- `POST /api/auth/login` `{username, password}`：成功 200 + cookie；失败 401（`用户名或密码错误`）。每个 IP + username 每分钟最多 5 次尝试。
- `POST /api/auth/logout`：清 cookie，204。
- `GET /api/auth/me`：`{id, username, email, is_admin, avatar_url}`；未登录 401。`avatar_url` 未上传时为 null。
- `POST /api/auth/password` `{old_password, new_password}`：需登录。校验当前密码后更新哈希；新密码 8-72 UTF-8 字节且不得与旧密码相同。当前密码错误 → 400。每用户 15 分钟最多 5 次。
- `POST /api/auth/avatar` multipart 字段 `file`：JPG/PNG/WebP/GIF，≤1.5MB，服务端裁成 256² WebP 存 `data/avatars/{id}.webp`。每用户每小时最多 10 次。
- `DELETE /api/auth/avatar`：清除自定义头像。
- `GET /api/auth/avatar/{user_id}`：返回 WebP；未设置 404。需登录。
- 用户 JSON 一律不含 password_hash。

## 路由

### `app/routers/problems.py`

- `GET /api/problems?difficulty=&source=&tag=&q=` → `[{id, slug, leetcode_id, title, difficulty, source, tags, my_status}]`，只含 `is_published=True`。`my_status`：`solved`（有 AC 提交）/ `attempted`（有提交无 AC）/ `null`。q 匹配 title/slug 子串（大小写不敏感）；纯数字时同时匹配 `leetcode_id`。
- `GET /api/problems/{slug}` → 详情：`{id, slug, leetcode_id, title, difficulty, source, tags, statement_md, time_limit_ms, memory_limit_mb, samples, leetcode_available, leetcode_starters?}`。`leetcode_starters` 为 `{python3, cpp}` 力扣官方风格模板（仅当本题有函数签名时）。404 不存在或未发布。

### `app/routers/submissions.py`

- `POST /api/submissions` body `{problem_slug, language, io_mode?, code}`：language ∈ {python3, cpp}，io_mode ∈ {acm, leetcode}（默认 acm），code ≤ 64KB。`leetcode` 且本题无函数签名 → 400。全局 pending/judging ≥ 10、该用户最近一分钟提交 ≥ 10，或该用户 pending/judging ≥ 2 时返回 429。成功 202 → `{id, status: "pending"}`。
- `GET /api/submissions/{id}` → 仅本人或管理员：`{id, problem_slug, problem_title, language, io_mode, code, status, runtime_ms, compile_output, detail, created_at}`。detail 结构见 `judge.md`。
- `GET /api/submissions?problem_slug=&limit=50` → 我的提交列表（不含 code，含 io_mode，新→旧）。

### `app/routers/drafts.py`

- `GET /api/drafts/{slug}?language=python3&io_mode=acm` → `{code, updated_at, is_default}`；无草稿时返回该语言+模式默认模板（is_default=true）。ACM 模板为完整 `main`；力扣模板为 `class Solution` / 设计类（签名与力扣一致）。力扣草稿存在 `python3_lc` / `cpp_lc` 语言键下，与 ACM 草稿隔离。本题无函数签名且 `io_mode=leetcode` → 400。
- `PUT /api/drafts/{slug}` body `{language, io_mode?, code}` → upsert，返回 `{updated_at}`。code ≤ 64KB。

### `app/routers/jobs.py`

- `GET /api/jobs` → 全部，按 deadline_at 升序（NULL 最后），返回完整字段 + `days_left`（可空）。`apply_url` 只允许有效 HTTPS；历史非法值在输出边界清空。
- `GET /api/jobs/track` → 当前用户 `{job_id: status}` 映射；`PUT /api/jobs/{id}/track` upsert 进度，`status=none` 时删除该记录。
- 管理员：`POST /api/jobs`、`PUT /api/jobs/{id}`、`DELETE /api/jobs/{id}`（204）。删除岗位前必须删除关联 `JobTrack`，避免 SQLite 外键失败；非管理员 403。

### `app/routers/quiz.py`

- `GET /api/quiz/banks`、`GET /api/quiz/questions`、`GET /api/quiz/questions/{id}` 提供专题统计、筛选分页和题目详情。
- 只有 `attempts_count > 0` 才算已作答。收藏或斩题可以创建偏好记录，但题目仍属于 `unanswered`，不得返回标准答案、解析、用户答案或对错，也不得计入专题和总览的作答/正确/错误/今日统计。
- `POST /api/quiz/questions/{id}/answer` 提交并判分，增加作答次数和错误次数，返回标准答案与解析；只有实际提交答案才更新用于“今日刷题”的时间。
- `POST /api/quiz/questions/{id}/favorite` 与 `/slash` 切换收藏、斩题状态，不修改最后作答时间。`GET /api/quiz/stats?tz_offset=` 按客户端时区返回总题数、作答、正确、错题、收藏、斩题、正确率和今日作答数。

### `app/routers/links.py`

- `GET /api/links` → 读取 `app/data/links.json`（仓库内置，字段 `[{category, title, url, note?}]`），内容为小林笔记（xiaolincoding.com）各栏目外链，含"大模型面试"分类。target=_blank 由前端处理。

### 管理员题目维护（`app/routers/admin.py`，全部要求 is_admin，否则 403）

- `POST /api/admin/seed/reload` → 同步导入算法题库与八股 JSON，返回 `{imported, quiz_imported}`。八股导入按选项原文重映射已有作答字母，不清 `quiz_records`。
- `PUT /api/admin/problems/{id}` body `{is_published}` → 上下架。
- `GET /api/admin/problems` → 含未发布的完整列表。
- `POST /api/admin/invites` body `{expires_in_days: 1..30}` → 创建并仅本次返回原始邀请码；`GET /api/admin/invites` → 列表（不含原始码）；`DELETE /api/admin/invites/{id}` → 撤销尚未使用的邀请码。

## 种子加载（`app/seed/loader.py`）

- 扫描 `app/seed/problems/*/`，解析 `meta.toml`（tomllib）+ `statement.md` + `tests/NNN.in|NNN.out`。格式详见 `seed-format.md`。
- 按 slug upsert：存在则更新字段并**删除旧 testcases 后重建**；不存在则插入。`python -m app.seed.loader` 可独立运行，也供 admin 路由调用。打印导入数量。
- meta.toml 中 `samples = [1, 2]` 指定哪些用例公开。
- `python -m app.seed.import_jobs <jobs.json>` 是岗位全量替换：先删除全部 `JobTrack`，再替换岗位，防止旧岗位 ID 对应到新数据。

## 测试（`backend/tests/`）

pytest + FastAPI TestClient，用临时目录 SQLite。覆盖邀请码注册、认证限流、生产 Origin/配置、题目与草稿、提交队列限制、jobs CRUD/URL、防御性备份和判题 worker 核心流程。

## 运行

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
