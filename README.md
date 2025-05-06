<div align="center">
  <img src="images/logo.png" width="400" alt="FreeTex">
</div>

<div align="center">
  <img src="https://img.shields.io/badge/版本-0.1.0-blue" alt="版本">
  <a href="LICENSE"><img src="https://img.shields.io/badge/许可证-AGPL3.0-green" alt="许可证"></a>
  <h4>
    <a href="README.md">🇨🇳 中文</a>
    <span> | </span>
    <a href="README_EN.md">🇬🇧 English</a>
  </h4>
</div>

## 🌟 简介

FreeTex是一个免费的公式智能识别软件，它可以识别图像中的数学公式并将其转换为可编辑的Latex格式。

特点：

- 无需联网免排队  
  采用本地部署的模型，无需联网调用，数据隐私得到充分保障

- 自适应显卡加速    
  自动调用独立显卡进行推理，秒出识别结果

- 多类型图像识别
  支持手写、印刷、扫描等多种类型的图像识别

- 傻瓜操作超简单
  支持上传图像、截图、粘贴三种操作模式，并支持快捷键，提升效率

- 结果导出多格式
  识别结果支持直接一键复制成word或latex格式，无需额外操作

- 软件多平台支持
  使用python构建，支持Windows、Linux、MacOS等不同平台运行

视频演示及操作教程：

[![FreeTex：免费的智能公式识别神器](https://i0.hdslb.com/bfs/archive/54175a1a4552c6236d05188bb63ff9ff26ccea54.jpg@672w_378h_1c.avif)](https://www.bilibili.com/video/BV1zPV2zVEMG)

## 📦 使用方式

### 1. 快速使用

1. windows系统：下载软件安装包：[https://pan.baidu.com/s/1wrI1lGRUso1HzO8ucrD9-g?pwd=8888](https://pan.baidu.com/s/1wrI1lGRUso1HzO8ucrD9-g?pwd=8888) (提取码: 8888) 

2. 打开软件，开始使用

具体使用方式可参考：https://blog.csdn.net/qq1198768105/article/details/147739708

### 2. 源码运行

#### 配置环境

创建新环境
```bash
conda create -n freetex python=3.10
conda activate freetex
```

安装依赖:
```bash
pip install -r requirements.txt
```

由于unimernet的requirements会自动安装最新CPU版的pytorch，需要卸载并重新安装gpu版本的pytorch(及对应的torchvision):
```bash
pip install torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu118
```

#### 下载模型

下载unimernet_small模型放置在`models`下:

下载方式：
```bash
cd models
git lfs install
git clone https://huggingface.co/wanderkid/unimernet_small
```

#### 运行软件

```bash
python main.py
```

运行后，软件操作方式与上一节相同。

# 🏗️ 项目结构

```
d:/Code/FreeTex/
├── main.py                     # 主应用程序入口
├── README.md                   # 项目说明文件
├── requirements.txt            # Python 依赖库列表
├── images/                     # 存放图片资源
│   └── ...
├── logs/                       # 存放日志文件
│   └── FreeTex.log
├── models/                     # 存放模型相关文件
│   ├── README.md               # 模型说明
│   └── unimernet_small/        # 模型文件目录 
│       
├── qfluentwidgets/             # PyQt-Fluent-Widgets 库
└── tools/                      # 工具模块
    ├── screenshot.py           # 截图工具
    ├── clipboard_handler.py    # 剪贴板处理器
    └── local_processor.py      # 本地模型处理器
```

## 📄 社群
如果有产品使用问题或建议，可加入交流群进行讨论。

<div align="center">
  <img src="docs/images/group.jpg" width="200" alt="交流群二维码">
</div>

## 🚀 鸣谢

本项目基于以下开源项目开发：

- [UniMERNet](https://github.com/opendatalab/UniMERNet)

- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)
