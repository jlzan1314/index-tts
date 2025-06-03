FROM pytorch/pytorch:2.7.0-cuda12.8-cudnn9-devel

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    ffmpeg \
    && apt-get clean

COPY requirements.txt /app/

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir --retries 20 --timeout 3000 -r requirements.txt

COPY . /app/

# 暴露API服务端口
EXPOSE 8000

# 设置环境变量
ENV HOST=0.0.0.0
ENV PORT=8000
ENV MODEL_DIR=/app/checkpoints
ENV CLEANUP_ENABLED=true
ENV FILE_MAX_AGE=3600
ENV CLEANUP_INTERVAL=3600

# 启动FastAPI服务
CMD ["python", "api.py", "--host", "${HOST}", "--port", "${PORT}", "--model_dir", "${MODEL_DIR}"]
