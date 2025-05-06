<div align="center"> 
  <img src="images/logo.png" width="400" alt="FreeTex">
</div>


<div align="center">
  <img src="https://img.shields.io/badge/Version-0.1.0-blue" alt="Version">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-AGPL3.0-green" alt="License"></a>
  <h4>
    <a href="README.md">🇨🇳 中文</a>
    <span> | </span>
    <a href="README_EN.md">🇬🇧 English</a>
  </h4>
</div>


## 🌟 Introduction

**FreeTex** is a free intelligent formula recognition tool that can identify mathematical formulas from images and convert them into editable LaTeX format.

### Features:

- **Offline & Queue-Free**  
  Utilizes locally deployed models, no internet required, ensuring full data privacy.

- **GPU Acceleration**  
  Automatically leverages your dedicated GPU for instant inference results.

- **Multi-Type Image Recognition**  
  Supports handwritten, printed, scanned, and other image types.

- **User-Friendly Operation**  
  Supports uploading, screenshotting, and pasting images, with shortcut key support for efficiency.

- **Multi-Format Export**  
  One-click export to Word or LaTeX format—no extra steps needed.

- **Cross-Platform Support**  
  Built with Python, compatible with Windows, Linux, and macOS.

Demo video and tutorial:

[![FreeTex: The Free Intelligent Formula Recognition Tool](https://i0.hdslb.com/bfs/archive/54175a1a4552c6236d05188bb63ff9ff26ccea54.jpg@672w_378h_1c.avif)](https://www.bilibili.com/video/BV1zPV2zVEMG)

## 📦 How to Use

### 1. Quick Start

1. **Windows Users**: Download the installation package:  
   [https://pan.baidu.com/s/1wrI1lGRUso1HzO8ucrD9-g?pwd=8888](https://pan.baidu.com/s/1wrI1lGRUso1HzO8ucrD9-g?pwd=8888) (Password: 8888)

2. Launch the application and start using it.

For detailed instructions, refer to:  
https://blog.csdn.net/qq1198768105/article/details/147739708

### 2. Run from Source

#### Set Up Environment

Create a new environment:

```bash
conda create -n freetex python=3.10
conda activate freetex
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Since `unimernet`'s requirements automatically install the latest **CPU** version of PyTorch, uninstall it and install the **GPU** version:

```bash
pip install torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu118
```

#### Download Model

Download the `unimernet_small` model and place it in the `models` directory:

```bash
cd models
git lfs install
git clone https://huggingface.co/wanderkid/unimernet_small
```

#### Run the Application

```bash
python main.py
```

After running, usage is the same as described in the previous section.

## 🏗️ Project Structure

```
d:/Code/FreeTex/
├── main.py                     # Main application entry point
├── README.md                   # Project documentation
├── requirements.txt            # Python dependencies
├── images/                     # Image assets
│   └── ...
├── logs/                       # Log files
│   └── FreeTex.log
├── models/                     # Model files
│   ├── README.md               # Model description
│   └── unimernet_small/        # Model directory 
│       
├── qfluentwidgets/             # PyQt-Fluent-Widgets library
└── tools/                      # Utility modules
    ├── screenshot.py           # Screenshot tool
    ├── clipboard_handler.py    # Clipboard handler
    └── local_processor.py      # Local model processor
```

## 📄 Community

For questions or suggestions, feel free to join the discussion group:

<div align="center">
  <img src="docs/images/group.jpg" width="200" alt="Community Group QR Code">
</div>


## 🚀 Acknowledgements

This project is developed based on the following open-source projects:

- [UniMERNet](https://github.com/opendatalab/UniMERNet)

- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)