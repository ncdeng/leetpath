#!/usr/bin/env bash
# 服务器一键升级：拉代码 → 按根目录 VERSION 构建带标签镜像 → 重启 → 健康检查 → 同步题库
# 用法：scripts/upgrade.sh             （升级当前分支）
# 回滚：scripts/upgrade.sh v<旧版本>   （切到指定 tag/ref 后部署）
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "$#" -gt 1 ]]; then
  echo "用法: scripts/upgrade.sh [tag-or-ref]" >&2
  exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "工作区有未提交改动，拒绝升级或回滚" >&2
  exit 1
fi

target_ref="${1:-}"
if [[ -n "$target_ref" ]]; then
  git fetch origin --tags
  git rev-parse --verify "${target_ref}^{commit}" >/dev/null
  git checkout --detach "$target_ref"
elif git symbolic-ref --quiet HEAD >/dev/null; then
  git pull --ff-only
else
  echo "==> 当前为 detached HEAD，跳过 git pull，部署当前提交 $(git rev-parse --short HEAD)"
fi

export LEETPATH_VERSION="$(tr -d '\r\n' < VERSION)"
if [[ ! "$LEETPATH_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "VERSION 必须是 x.y.z，当前值：$LEETPATH_VERSION" >&2
  exit 1
fi

version_tag="v$LEETPATH_VERSION"
if git rev-parse --verify --quiet "refs/tags/$version_tag" >/dev/null; then
  tagged_commit="$(git rev-list -n 1 "$version_tag")"
  current_commit="$(git rev-parse HEAD)"
  if [[ "$tagged_commit" != "$current_commit" ]]; then
    echo "$version_tag 已指向其他提交；请先发布新版本，拒绝覆盖同版本镜像" >&2
    exit 1
  fi
fi
echo "==> 升级到 v$LEETPATH_VERSION"

docker compose build backend frontend
# 判题沙箱镜像（judge-python/judge-cpp）不随升级重建；
# 仅在 backend/judge/Dockerfile.* 变化时手动执行：
#   docker compose --profile judge-images build

docker compose --profile production up -d --remove-orphans

echo "==> 等待 backend 健康检查..."
healthy=0
for _ in $(seq 1 30); do
  if health_body="$(docker compose exec -T backend curl -fsS http://localhost:8000/api/health 2>/dev/null)"; then
    if [[ "$health_body" != *"\"version\":\"$LEETPATH_VERSION\""* ]]; then
      echo "健康检查版本不一致：期望 $LEETPATH_VERSION，实际响应 $health_body" >&2
      exit 1
    fi
    echo "$health_body"
    healthy=1
    break
  fi
  sleep 2
done
if [[ "$healthy" -ne 1 ]]; then
  echo "健康检查超时，请查看: docker compose logs backend" >&2
  exit 1
fi

echo "==> 同步算法题库（保留用户、提交、草稿与记忆记录）..."
docker compose exec -T backend python -m app.seed.loader

echo "==> 导入八股题库（按选项原文重映射作答字母，不清 quiz_records）..."
docker compose exec -T backend python -m app.seed.quiz_loader

echo "==> v$LEETPATH_VERSION 升级完成"
