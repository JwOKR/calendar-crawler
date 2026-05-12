#!/usr/bin/env python3
"""
启动脚本：读取 PORT 环境变量并启动 uvicorn
"""
import os
import sys

port = int(os.getenv("PORT", 8000))
print(f"Starting uvicorn on 0.0.0.0:{port}")

sys.path.insert(0, "/app")
import uvicorn
from app.main import app

uvicorn.run(app, host="0.0.0.0", port=port)
