#!/usr/bin/env bash
# 服务器一键升级：拉代码 → 按根目录 VERSION 构建带标签镜像 → 重启 → 健康检查
# 用法：scripts/upgrade.sh        （升级）
# 回滚：git checkout v<旧版本> 后重新执行本脚本即可（detached HEAD 下会自动跳过 git pull）
set -euo pipefail
cd "$(dirname "$0")/.."

# set -e 下 detached HEAD 的 pull 必失败且会当场退出，回滚流程就走不到构建了；
# 显式识别回滚场景跳过 pull，正常分支上 pull 失败仍应中止（避免用旧代码构建出新版本）
if [[ "$(git rev-parse --abbrev-ref HEAD)" == "HEAD" ]]; then
  echo "==> detached HEAD（回滚模式），跳过 git pull"
else
  git pull --ff-only
fi
export LEETPATH_VERSION="$(cat VERSION)"
echo "==> 升级到 v$LEETPATH_VERSION"

docker compose build backend frontend
# 判题沙箱镜像（judge-python/judge-cpp）不随升级重建；
# 仅在 backend/judge/Dockerfile.* 变化时手动执行：
#   docker compose --profile judge-images build

docker compose --profile production up -d --remove-orphans

echo "==> 等待 backend 健康检查..."
healthy=0
for _ in $(seq 1 30); do
  if docker compose exec -T backend curl -fsS http://localhost:8000/api/health 2>/dev/null; then
    echo
    healthy=1
    break
  fi
  sleep 2
done
if [[ "$healthy" -ne 1 ]]; then
  echo "健康检查超时，请查看: docker compose logs backend" >&2
  exit 1
fi

echo "==> 导入八股题库（按选项原文重映射作答字母，不清 quiz_records）..."
docker compose exec -T backend python -m app.seed.quiz_loader

echo "==> v$LEETPATH_VERSION 升级完成"
