FROM nvidia/cuda:11.6.2-cudnn8-runtime-ubuntu20.04

# 设置工作目录
WORKDIR /app

# 安装系统依赖和Python 3.10
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libxcb-shape0 \
    git \
    git-lfs \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y python3.10 python3.10-distutils python3.10-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装pip
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

# 创建Python和pip的软链接
RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    ln -sf /usr/bin/python3.10 /usr/bin/python3

# 复制项目文件
COPY . /app/

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 下载模型
RUN mkdir -p models && \
    cd models && \
    git lfs install && \
    git clone https://huggingface.co/wanderkid/unimernet_small

# 设置环境变量
ENV QT_QPA_PLATFORM=offscreen
ENV PYTHONPATH=/app

# 运行应用
CMD ["python", "main.py"]

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility