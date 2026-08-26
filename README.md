# leetpath

响应式个人刷题站：力扣热题 100 + 面经高频手撕题库，Python3 / C++ 在线评测（Docker 沙箱），草稿入库多端同步，首页校招看板，大模型八股外链小林笔记。

题面用例为 ACM 模式（stdin / stdout）；刷题页可切换力扣函数模式（`class Solution`），由评测套上读入 harness。本仓库仅供个人学习使用。

## 功能

- 热题 100 与面经手撕：题面 Markdown、样例与隐藏用例、按难度 / 来源 / 标签筛选
- 在线评测：Python3 与 C++，ACM 标准输入输出或力扣函数模式可切换；状态 `pending / judging / AC / WA / TLE / MLE / CE / RE / IE`
- 代码草稿入库，登录后多端同步
- 校招看板：岗位、批次、截止日、投递链接（管理员 CRUD）
- 八股外链：小林笔记（含大模型面试栏目）
- 响应式 SPA：桌面双栏刷题，移动端 Tab

## 技术栈

- 后端：FastAPI + SQLAlchemy 2.x + SQLite（WAL），JWT HttpOnly Cookie（bcrypt）
- 前端：Vue 3 + Vite + TypeScript + CodeMirror 6 + marked / dompurify，手写 CSS（断点 768px / 1024px）
- 判题：独立 worker 轮询 SQLite，每次提交起一次性 Docker 容器（`--network none --read-only`）
- 部署：docker compose + Cloudflare Tunnel（nginx 静态 + `/api` 反代 / backend / judge worker / SQLite 备份）

## 本地开发

需要 Python ≥ 3.12、Node.js 22+。判题另需本机 Docker。

### 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

管理员不会通过公开注册产生。首次启动后执行 `python -m app.manage create-admin owner` 创建管理员，再由管理员在管理页生成一次性邀请码。开发期 CORS 放行 `http://localhost:5173`。

```bash
cd backend && pytest
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

开发服务器在 5173，`/api` 代理到 `http://localhost:8000`。

### 种子导入 / 校验

```bash
# 导入题库（在 backend/ 目录）
python -m app.seed.loader

# 导入八股客观题库（750 题含 Agent Harness，/quiz 页面数据源）
python -m app.seed.quiz_loader

# 校验参考解与用例（仓库根目录）
python scripts/validate_seed.py
python scripts/validate_seed.py two-sum
```

也可登录管理员账号后调用 `POST /api/admin/seed/reload`，或在前端「管理」页重新导入。

### 判题 worker

先在本机构建评测镜像，再于 `backend/` 下启动 worker（与 API 共用同一个 SQLite）：

```bash
cd backend
docker build -t leetpath-judge-python -f judge/Dockerfile.python judge
docker build -t leetpath-judge-cpp    -f judge/Dockerfile.cpp judge
python -m judge.worker
```

`DATABASE_URL` 需与后端一致（默认 `sqlite:///data/leetpath.db`，相对 `backend/`）。

## 生产部署（域名 + Cloudflare Tunnel）

目标是浏览器直接打开 HTTPS 域名，使用者无需安装客户端；VPS 不开放 80/443/8000。宿主机需要 Linux、Docker 与 Compose。judge 容器挂载 `/var/run/docker.sock`，在宿主 daemon 上启动一次性评测容器，因此**判题镜像必须打到宿主机**。

1. 将已购买域名接入 Cloudflare DNS。在 Zero Trust 的 Networks → Tunnels 新建 Cloudflared Tunnel，复制 Docker connector 的 token；为 Tunnel 添加 Public Hostname，例如 `learn.example.com`，Service 选择 `HTTP`，URL 填 `frontend:80`。建议再为该应用配置 Cloudflare Access，只允许好友邮箱。

2. 复制并填写生产配置：

   ```bash
   cp .env.example .env
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   sed -i "s|^DOCKER_GID=.*|DOCKER_GID=$(stat -c %g /var/run/docker.sock)|" .env
   ```

   将生成值写入 `SECRET_KEY`，同时填写 `PUBLIC_ORIGIN=https://learn.example.com` 和 `CLOUDFLARE_TUNNEL_TOKEN`。`DOCKER_GID` 由上面的 sed 命令自动填入（judge 容器以非 root 运行，需借宿主 docker 组访问 docker.sock）。`APP_ENV=production` 与 `COOKIE_SECURE=true` 必须保留；配置不安全时后端会拒绝启动。不要提交 `.env`。没有 `.env` 时 `docker compose --profile production config` 仍可解析（`env_file` 允许缺失）；真正启动生产仍须先复制并填写 `.env`。

3. VPS 防火墙只保留必要的 SSH 入站，SSH 还应限制来源或使用密钥登录。应用所有容器都没有宿主端口映射，cloudflared 通过出站连接接入 Cloudflare。

4. 创建判题临时目录（属主须与容器内用户 10001 一致），构建判题镜像并启动生产 profile：

   ```bash
   sudo install -d -o 10001 -g 10001 /var/lib/leetpath/judge-tmp
   docker compose build judge-python judge-cpp
   docker compose --profile production up -d --build
   ```

5. 创建管理员并导入题库：

   ```bash
   docker compose exec backend python -m app.manage create-admin owner
   docker compose exec backend python -m app.seed.loader
   docker compose exec backend python -m app.seed.quiz_loader
   ```

6. 打开 `https://learn.example.com`，用管理员账号登录，在「管理 → 邀请码」生成邀请码并发给好友。邀请码只显示一次、只能使用一次，可设置 1-30 天有效期或在使用前撤销。

常用命令：`docker compose --profile production logs -f`、`docker compose --profile production down`。

### AI 助教出网

填了中转站 key 之后，如果 `/api/ai/models` 返回 502，是因为 backend 当时只挂在 `internal` 的 `app` 网上，容器访问不了公网。`docker-compose.yml` 里 backend 需要再挂一条非 internal 的 `egress` 网；judge / backup 仍只留在 `app`。改完执行 `docker compose --profile production up -d` 即可，**不要** `down -v`（会删数据库卷）。

中转站域名还要写进 `.env` 的 `AI_ALLOWED_HOSTS`（逗号分隔）。现有示例：

```
AI_ALLOWED_HOSTS=api.antithor.asia,api.deepseek.com
```

换站或加域名就在后面追加，例如 `,your-relay.example.com`，然后只重启 backend，不动数据库。
主数据库在 `leetpath-data`，每日在线快照在 `leetpath-backups`，默认保留 7 份。两者仍在同一台 VPS，需定期将 `/app/backups/leetpath-*.db` 导出到异机或对象存储，并实际演练恢复。

### 升级版本（不丢用户数据）

用户、提交、草稿、头像、八股作答、校招进度都在 **Docker named volume** 里，不在镜像里。`scripts/upgrade.sh` 只拉代码、按根目录 `VERSION` 重建 `leetpath-backend:<版本>` / `leetpath-frontend:<版本>`、再 `up -d` 换容器，**不会删 volume**。启动时 `create_all` + `ensure_schema` 只给旧库加列，不会 drop 表。

本地发版（有新功能要上生产时）：

```bash
# VERSION 已改好则直接打标签；否则用脚本改 VERSION 并提交
# scripts/release.sh 0.3.1
git tag v0.3.1
git push && git push origin v0.3.1
```

服务器上（在有 `docker-compose.yml` 和 `.env` 的仓库根目录）：

```bash
# 1. 升之前拍一份在线备份（推荐）
docker compose --profile production exec -T backup python -c "
from pathlib import Path
from app.backup import backup_once
print(backup_once(Path('/app/data/leetpath.db'), Path('/app/backups')))
"

# 2. 拉代码、按 VERSION 构建并滚动重启；脚本末尾会导入八股
#    （按选项原文重映射作答字母，对错/收藏/斩题保留，不清 quiz_records）
git pull --ff-only
scripts/upgrade.sh
```

`upgrade.sh` 成功后 `/api/health` 的 `version` 应等于仓库里的 `VERSION`。账号、提交记录、草稿都还在。八股导入也可在管理页点「重新导入题库与八股」。

若 `git pull --ff-only` 因历史改写失败，在确认没有未提交的服务器改动后：`git fetch origin && git reset --hard origin/main`（`.env` 不在 git 里，不会被删）。

回滚到上一版（同样不碰数据库）：

```bash
git checkout v0.2.2
scripts/upgrade.sh
```

回到最新：`git checkout main && git pull --ff-only && scripts/upgrade.sh`。

**这些才会丢掉用户数据，不要用：**

- `docker compose down -v`（`-v` 会删掉 `leetpath-data` / `leetpath-backups`）
- `docker volume rm …leetpath-data`、`docker volume prune`
- 用一份空的 `leetpath.db` 覆盖 `/app/data/`
- 把整个项目目录当一次性目录删掉并且卷也清了

`docker compose --profile production down`（**没有** `-v`）再 `up -d` 是安全的，库还在。

管理页「重新导入种子 / 八股」会更新题面和选项，**不会删用户表**。但八股若打乱了选项字母，用户以前存的「我选了 B」会对到新文案上。升代码不必点导入；只有要改题库内容时再点。

判题沙箱镜像（`leetpath-judge-python` / `leetpath-judge-cpp`）默认不随 `upgrade.sh` 重建。改了 `backend/judge/Dockerfile.*` 时再手动：

```bash
docker compose --profile judge-images build
```

### 备份恢复

先用 `docker compose --profile production exec backup ls -lh /app/backups` 查看快照，再用 `docker compose --profile production cp backup:/app/backups/<文件名> ./restore/leetpath.db` 导出。恢复时：

```bash
docker compose --profile production stop backend judge backup
docker compose run --rm --no-deps -v "$PWD/restore:/restore:ro" backend sh -c \
  'cp /app/data/leetpath.db /app/data/leetpath.db.failed && rm -f /app/data/leetpath.db-wal /app/data/leetpath.db-shm && cp /restore/leetpath.db /app/data/leetpath.db'
docker compose --profile production up -d
docker compose exec backend python -c "import sqlite3; print(sqlite3.connect('/app/data/leetpath.db').execute('PRAGMA integrity_check').fetchone()[0])"
```

完整性检查必须输出 `ok`，随后再做登录和提交烟测。不要直接复制正在运行的 WAL 数据库文件替代在线备份。

## 目录结构

```
.
├── backend/
│   ├── app/                 # FastAPI：models / routers / auth / seed
│   ├── judge/               # worker 与判题镜像 Dockerfile
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/                 # Vue SPA
│   └── Dockerfile
├── deploy/nginx.conf        # 静态站点 + /api 反代
├── docs/spec/               # 模块规格
├── docs/seed/               # 热题 100 清单
├── scripts/validate_seed.py
├── scripts/release.sh       # 本地改 VERSION 并打 tag
├── scripts/upgrade.sh       # 服务器拉代码、按 VERSION 构建并重启（不删 volume）
├── docker-compose.yml
└── .env.example
```

## 添加新题 / 面经题

每题一个目录 `backend/app/seed/problems/<slug>/`（`meta.toml` + `statement.md` + `tests/` + `reference.py`），`source` 取 `hot100` 或 `mianjing`。格式与 I/O 约定见 [docs/spec/seed-format.md](docs/spec/seed-format.md)。写完后在仓库根目录执行 `python scripts/validate_seed.py <slug>`，再 `python -m app.seed.loader`（或管理页「重新导入种子」）。

## 安全注意事项

- **docker.sock**：judge 服务把宿主 Docker 套接字挂进容器，等价于该容器可操控宿主机 Docker（通常即 root）。应使用不承载其他重要服务的专用 VPS；评测子容器的隔离参数不能消除 worker 持有 socket 的风险。
- **题库版权**：题面与用例仅限个人学习，请勿公开传播或用于商业用途。
- **入口与密钥**：不要提交 `.env` 或 Tunnel token。不要恢复任何宿主端口映射；生产环境必须使用随机 `SECRET_KEY`、HTTPS `PUBLIC_ORIGIN` 与 `COOKIE_SECURE=true`。
