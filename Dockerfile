FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（Playwright 已预装）
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码和启动脚本
COPY app/ ./app/
COPY start.py ./
RUN mkdir -p data

# 暴露端口
EXPOSE 8000

# 启动命令：使用 start.py 脚本（自动读取 PORT 环境变量）
CMD ["python", "start.py"]
