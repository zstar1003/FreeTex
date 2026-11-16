<div align="center">
  <img src="resources/images/logo.png" width="400" alt="FreeTex">
</div>

<div align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="version">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-AGPL3.0-green" alt="License"></a>
  <h4>
    <a href="README.md">🇨🇳 Chinese</a>
    <span> | </span>
    <a href="README_EN.md">🇬🇧 English</a>
  </h4>
</div>

## 🌟 Introduction

FreeTex is a free intelligent formula recognition software that can identify mathematical formulas in images and convert them into editable Latex format.

Video demonstration and operation tutorial:

[![FreeTex: Free intelligent formula recognition artifact](https://i0.hdslb.com/bfs/archive/54175a1a4552c6236d05188bb63ff9ff26ccea54.jpg@672w_378h_1c.avif)](https://www.bilibili.com/video/BV1zK31zKEPp)

Want to edit the recognition result? You can check out my tool station: https://xdxsb.top/FreeTool

## 📦 How to use

### 1. Quick use

1. Download software

- windows system:

  - [Github](https://github.com/zstar1003/FreeTex/releases/download/v1.0.0/FreeTex_setup_v1.0.0.exe)
  - [kuake](https://pan.quark.cn/s/6d094961e2c3)

- macos system (arm):

  - Method 1: Direct download: [Github](https://github.com/zstar1003/FreeTex/releases/download/v1.0.0/FreeTex-Installer-1.0.0.dmg)
  - Method 2: Install using Homebrew: `brew install freetex`


2. Install the software and start using it

  For specific usage, please refer to the adaptation tutorial above.

> [!NOTE]
> When using the windows version, the software needs to be placed in a non-Chinese path, otherwise it will not start normally.

### 2. Source code execution

> [!NOTE]
> Please note: The main branch is developed in a mac environment. If it is a windows environment, it is recommended to switch to the win branch of this project.

#### Configure environment

uv:
```bash
uv sync
```

#### Download model

Download the unimernet_small model and place it under `models`:

Download method:
```bash
cd models
git lfs install
git clone https://huggingface.co/wanderkid/unimernet_small
```

#### Run the software

```bash
python main.py
```

After running, the software operates in the same manner as in the previous section.


## 🚀 Acknowledgments

This project is developed based on the following open source projects:

- [UniMERNet](https://github.com/opendatalab/UniMERNet)

- [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)

- [KaTeX](https://github.com/KaTeX/KaTeX)

Thanks to the contributors to this project:

<a href="https://github.com/zstar1003/FreeTex/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=zstar1003/FreeTex" />
</a>

## Star History

![Star History](https://starchart.cc/zstar1003/FreeTex.svg)
### Multimodal connection check

The **测试模型列表** (Test model list) button only requests `/models` from the configured service. It does not upload an image or run model inference. Success does not verify the selected model's vision capabilities; failure may only mean the service does not support listing models. Actual recognition sends the selected model and image to `/chat/completions` and must be verified separately.

The check runs in the background and ignores repeated clicks while pending. Network timeouts are set to 10 seconds with automatic retries disabled. Closing the dialog does not wait for the request or show its late result; an already-started read-only request finishes in the background and closes its client. This is a network-operation timeout, not a strict total-duration deadline. Exiting the entire application may still wait for outstanding pool tasks to finish.
