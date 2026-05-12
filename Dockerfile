FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（Playwright 已预装）
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
RUN mkdir -p data

# 暴露端口
EXPOSE 8000

# 启动命令：用 Python 读取 PORT 环境变量
CMD ["python", "-c", "import os, uvicorn; from app.main import app; uvicorn.run(app, host='0.0.0.0', port=int(os.getenv('PORT', 8000)))"]
