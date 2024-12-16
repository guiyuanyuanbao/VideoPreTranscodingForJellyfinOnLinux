#!/bin/bash

# 启动 FastAPI 服务器
uvicorn app.main:app --host 0.0.0.0 --port 8096 &
FASTAPI_PID=$!
echo "启动 FastAPI，PID: $FASTAPI_PID"

# 等待 FastAPI 进程
wait $FASTAPI_PID

