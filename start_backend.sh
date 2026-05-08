#!/usr/bin/env bash
# 启动 emotion-sphere 后端（FastAPI）
# 用法：./start_backend.sh
# 环境变量可在 .env 文件或命令行中设置

set -e

# 进入项目根目录
cd "$(dirname "$0")"

# 如果有 .env 文件，加载环境变量
if [ -f .env ]; then
  echo "[start] Loading .env file..."
  set -o allexport
  source .env
  set +o allexport
fi

# 检查必要环境变量
if [ -z "$DATABASE_URL" ]; then
  echo "[error] DATABASE_URL is not set."
  echo "  Example: postgresql://user:password@localhost:5432/emotion_sphere"
  echo "  Set it in .env or as environment variable."
  exit 1
fi

echo "[start] Starting Emotion Sphere backend on http://0.0.0.0:8000 ..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
