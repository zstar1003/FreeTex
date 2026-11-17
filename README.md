<div align="center">
  <img src="resources/images/logo.png" width="400" alt="FreeTex">
</div>

<div align="center">
  <img src="https://img.shields.io/badge/安装包-1.0.0-blue" alt="安装包版本">
  <a href="LICENSE"><img src="https://img.shields.io/badge/许可证-AGPL3.0-green" alt="许可证"></a>
  <h4>
    <a href="README.md">🇨🇳 中文</a>
    <span> | </span>
    <a href="README_EN.md">🇬🇧 English</a>
  </h4>
</div>

## 🌟 简介

FreeTex是一个免费的公式智能识别软件，它可以识别图像中的数学公式并将其转换为可编辑的Latex格式。

视频演示及操作教程：

[![FreeTex：免费的智能公式识别神器](https://i0.hdslb.com/bfs/archive/54175a1a4552c6236d05188bb63ff9ff26ccea54.jpg@672w_378h_1c.avif)](https://www.bilibili.com/video/BV1zK31zKEPp)

想对识别结果进行编辑？可以看看我的工具站：https://xdxsb.top/FreeTool

## 📦 使用方式

### 1. 快速使用

> [!IMPORTANT]
> 下方 GitHub 下载链接指向 **v1.0.0 安装包**，不等同于当前 `main` 源码。后文的后台模型列表检查、识别错误处理和用户目录设置迁移属于源码更新，不能据此认为旧安装包已包含这些修复。版本号仍为 `1.0.0` 也不能证明代码一致；请以源码提交和发布说明区分。

1. 下载软件

- windows系统：

  - [Github](https://github.com/zstar1003/FreeTex/releases/download/v1.0.0/FreeTex_setup_v1.0.0.exe)
  - [夸克网盘](https://pan.quark.cn/s/6d094961e2c3)

- macos系统(arm)：

  - 方式一；直接下载：[Github](https://github.com/zstar1003/FreeTex/releases/download/v1.0.0/FreeTex-Installer-1.0.0.dmg)
  - 方式二；用Homebrew进行安装：`brew install freetex`
  > [!NOTE]
  > v1.0.0 macOS 安装包的 `No module named 'openai'` 问题及维护者提供的历史补丁见 [issue #44](https://github.com/zstar1003/FreeTex/issues/44)。该补丁针对缺失依赖，不代表包含当前源码修复。


2. 安装软件，开始使用

  具体使用方式可参考上面的适配教程。

  > [!NOTE]
  > windows版本使用时需放置软件在非中文路径下，否则无法正常启动。

### 2. 源码运行

> [!NOTE]
> 请注意：主分支是在mac环境下进行开发，如果是windows环境，建议切换至本项目的win分支。

#### 配置环境

uv:
```bash
uv sync
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
## 当前 main 源码行为（非 v1.0.0 安装包承诺）

以下说明对应 [PR #52](https://github.com/zstar1003/FreeTex/pull/52)、[PR #53](https://github.com/zstar1003/FreeTex/pull/53)、[PR #54](https://github.com/zstar1003/FreeTex/pull/54) 和 [PR #55](https://github.com/zstar1003/FreeTex/pull/55) 合入后的 `main`；不自动适用于 `win` 分支或旧 release。

本次仅核对源码、发布资产元数据和 issue，未直接安装验证 DMG/EXE、历史补丁、签名或公证。源码合并不会替换已有发布资产，也不表示新版完整安装包已经发布。

### 多模态设置中的连接检查

“测试模型列表”仅请求配置服务的 `/models`，不发送图片、不执行模型推理。成功不代表所选模型支持视觉识别；失败也可能仅表示服务不支持模型列表接口。实际识别通过 `/chat/completions` 发送所选模型和图片，需要单独验证。

检查在后台执行，期间禁用重复点击；网络超时设为 10 秒且不自动重试。关闭设置窗口不会等待请求，也不会显示其迟到结果；已开始的只读请求会在后台结束并释放客户端。此超时为网络操作超时，不是严格的总耗时上限。 退出整个应用时，线程池仍可能等待尚未完成的检查结束。

### 识别后端与错误处理

启用多模态识别后，识别请求不再要求本地模型加载成功。云端请求或配置读取失败会显示“识别失败”，不会静默改用本地模型，也不会显示成功提示或允许复制错误文本。需要本地识别时，请在设置中关闭多模态识别。本地模型初始化仍按现有启动流程执行，本改动不跳过启动加载，也不验证真实服务的兼容性。

### 设置文件位置与迁移

设置（包括 API Key）保存到当前用户目录，而不是打包资源 `_MEIPASS`：macOS 为 `~/Library/Application Support/FreeTex/config.json`，Windows 为 `%APPDATA%/FreeTex/config.json`，Linux 为 `$XDG_CONFIG_HOME/FreeTex/config.json`（未设置时使用 `~/.config`）。源码运行也使用同一用户目录。

首次读取会将当前可见的旧 `config.json` 迁移到用户目录，保留原文件；已有用户设置不会被新版内置默认值覆盖。迁移或解析失败不会覆盖旧文件，保存失败不会截断现有配置。已经随旧 onefile 临时目录消失的设置无法恢复。

配置仍是本机明文 JSON，不是密码保险库。新文件在 POSIX 上为仅用户可读写（0600）；Windows 使用用户配置目录的访问控制。请勿分享含 API Key 的配置文件。测试仅使用临时目录和合成凭据，未验证真实签名安装包或跨平台文件系统。

请避免多个 FreeTex 实例同时修改设置（普通保存采用进程内锁）；不支持硬链接的文件系统可能导致首次迁移明确失败，但原件会保留。
