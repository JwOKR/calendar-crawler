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

# 启动命令（支持 Railway 的 PORT 环境变量）
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
