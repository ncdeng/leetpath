#!/usr/bin/env bash
# 发布新版本：scripts/release.sh 0.3.2
# 更新 VERSION 单源并打 git tag，服务器端用 scripts/upgrade.sh 拉取升级
set -euo pipefail
cd "$(dirname "$0")/.."

new="${1:-}"
if [[ ! "$new" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "用法: scripts/release.sh <x.y.z>（当前 $(cat VERSION 2>/dev/null || echo 未知)）" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "工作区有未提交改动；请先提交完整修复，再发布 v$new" >&2
  exit 1
fi
if git rev-parse --verify --quiet "refs/tags/v$new" >/dev/null; then
  echo "标签 v$new 已存在，拒绝重复发布" >&2
  exit 1
fi

current="$(tr -d '\r\n' < VERSION)"
if [[ "$current" != "$new" ]]; then
  echo "$new" > VERSION
  git add VERSION
  git commit -m "release: v$new"
fi
git tag "v$new"
echo "已发布 v$new。推送代码与标签：git push && git push origin v$new"
