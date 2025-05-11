<div align="center">
  <img src="resources/images/logo.png" width="400" alt="FreeTex">
</div>

<div align="center">
  <img src="https://img.shields.io/badge/版本-0.2.0-blue" alt="版本">
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

1. 下载软件

windows系统(无需安装，开箱即用)：

- [百度网盘下载地址](https://pan.baidu.com/s/12rtlWi6S8PxHL2NQew5_rg?pwd=8888)(提取码: 8888)

- [夸克网盘下载地址](https://pan.quark.cn/s/65a205d8abb8)

macos系统：

- [百度网盘下载地址](https://pan.baidu.com/s/1NstYEU4TcWubJSAO8WcLTw?pwd=8888)(提取码: 8888)

- [夸克网盘下载地址](https://pan.quark.cn/s/dac20f982f53)


2. 安装软件，开始使用

具体使用方式可参考：https://blog.csdn.net/qq1198768105/article/details/147739708

> [!NOTE]
> windows版本使用时需放置软件在非中文路径下，否则无法正常启动。
> 软件只识别公式，不识别文字，公式须保持亮色背景(白色最佳)

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

#### 编译资源文件
```bash
cd resources
pyrcc5 resources/app.qrc -o resources/app_rc.py -compress 3
```

#### 运行软件

```bash
python main.py
```

运行后，软件操作方式与上一节相同。

# 🏗️ 项目结构

```
FreeTex/
├── .gitignore
├── .python-version
├── LICENSE
├── README.md                   # 项目说明文件
├── README_EN.md
├── config.json
├── demo.yaml
├── docs/                       # 文档目录
│   ├── images/                 # 文档图片
│   │   ├── group.jpg
│   │   ├── icon.ico
│   │   ├── icon.png
│   │   ├── logo.png
│   │   └── qrcode.jpg
│   ├── index.html
│   ├── script.js
│   └── style.css
├── libs/                       # 依赖库
│   ├── index.html
│   └── katex/                  # KaTeX库
│       ├── README.md
│       ├── contrib/
│       ├── fonts/
│       ├── katex.css
│       ├── katex.js
│       ├── katex.min.css
│       ├── katex.min.js
│       └── katex.mjs
├── main.py                     # 主应用程序入口
├── main.spec
├── models/                     # 存放模型相关文件
│   └── README.md               # 模型说明
├── pyproject.toml
├── qfluentwidgets/             # PyQt-Fluent-Widgets 库
│   ├── init .py
│   ├── _rc/
│   │   ├── init .py
│   │   ├── i18n/
│   │   ├── images/
│   │   ├── qss/
│   │   ├── resource.py
│   │   └── resource.qrc
│   ├── common/                 # 通用模块
│   │   ├── init .py
│   │   ├── animation.py
│   │   ├── auto_wrap.py
│   │   ├── color.py
│   │   ├── config.py
│   │   ├── exception_handler.py
│   │   ├── font.py
│   │   ├── icon.py
│   │   ├── image_utils.py
│   │   ├── overload.py
│   │   ├── router.py
│   │   ├── screen.py
│   │   ├── smooth_scroll.py
│   │   ├── style_sheet.py
│   │   ├── theme_listener.py
│   │   └── translator.py
│   ├── components/             # 组件模块
│   │   ├── init .py
│   │   ├── date_time/
│   │   ├── dialog_box/
│   │   ├── layout/
│   │   ├── material/
│   │   ├── navigation/
│   │   ├── settings/
│   │   └── widgets/
│   ├── multimedia/             # 多媒体模块
│   │   ├── init .py
│   │   ├── media_play_bar.py
│   │   ├── media_player.py
│   │   └── video_widget.py
│   └── window/                 # 窗口模块
│       ├── init .py
│       ├── fluent_window.py
│       ├── splash_screen.py
│       └── stacked_widget.py
├── requirements.txt            # Python 依赖库列表
├── resources/                  # 资源文件
│   ├── .gitignore
│   ├── init .py
│   ├── app.qrc
│   ├── fonts/                  # 字体文件
│   │   ├── Crimson_Pro/
│   │   └── Noto_Serif_SC/
│   ├── images/                 # 应用图片资源
│   │   ├── icon.icns
│   │   ├── icon.ico
│   │   ├── icon.png
│   │   └── logo.png
│   └── mathview/               # KaTeX渲染视图
│       └── index.html
├── scripts/                    # 构建脚本
│   └── build-macos.sh
├── test_imgs/                  # 测试图片
│   ├── 0000000.png
│   ├── ...
│   └── 0000014.png
├── tools/                      # 工具模块
│   ├── init .py
│   ├── clipboard_handler.py    # 剪贴板处理器
│   ├── local_processor.py      # 本地模型处理器
│   └── screenshot.py           # 截图工具
├── unimernet/                  # UniMERNet 模型相关
│   ├── init .py
│   ├── common/
│   │   ├── init .py
│   │   ├── config.py
│   │   ├── dist_utils.py
│   │   ├── gradcam.py
│   │   ├── logger.py
│   │   ├── optims.py
│   │   ├── registry.py
│   │   └── utils.py
│   ├── configs/                # 配置文件
│   │   ├── datasets/
│   │   ├── default.yaml
│   │   └── models/
│   ├── datasets/               # 数据集处理
│   │   ├── init .py
│   │   ├── builders/
│   │   ├── data_utils.py
│   │   └── datasets/
│   ├── models/                 # 模型定义
│   │   ├── init .py
│   │   ├── base_model.py
│   │   ├── blip2_models/
│   │   ├── clip_vit.py
│   │   ├── eva_vit.py
│   │   ├── unimernet/
│   │   └── vit.py
│   ├── processors/             # 数据预处理器
│   │   ├── init .py
│   │   ├── base_processor.py
│   │   ├── blip_processors.py
│   │   ├── formula_processor.py
│   │   ├── formula_processor_helper/
│   │   └── randaugment.py
│   ├── runners/                # 训练/评估运行器
│   │   ├── init .py
│   │   ├── runner_base.py
│   │   └── runner_iter.py
│   ├── tasks/                  # 任务定义
│   │   ├── init .py
│   │   ├── base_task.py
│   │   └── unimernet_train.py
└── uv.lock
```

## 📄 社群
如果有产品使用问题或建议，可加入交流群进行讨论。

由于群聊超过200人，无法通过扫码加入，如需加群，加我微信zstar1003，备注"加群"即可。

## 🚀 鸣谢

本项目基于以下开源项目开发：

- [UniMERNet](https://github.com/opendatalab/UniMERNet)

- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)

- [KaTeX](https://github.com/KaTeX/KaTeX)

感谢此项目贡献者们：

<a href="https://github.com/zstar1003/FreeTex/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=zstar1003/FreeTex" />
</a>

## Star History

![Star History](https://starchart.cc/zstar1003/FreeTex.svg)