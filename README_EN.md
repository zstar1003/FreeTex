<div align="center">
  <img src="resources/images/logo.png" width="400" alt="FreeTex">
</div>

<div align="center">
  <img src="https://img.shields.io/badge/installer-1.0.0-blue" alt="installer version">
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

> [!IMPORTANT]
> The GitHub download links below point to **v1.0.0 installers**, not the current `main` source. The background model-list check, recognition error handling and user-profile settings migration described later are source updates, not a promise that the old installers include them. A version string of `1.0.0` alone does not establish identical code; distinguish source commits from release notes.

1. Download software

- windows system:

  - [Github](https://github.com/zstar1003/FreeTex/releases/download/v1.0.0/FreeTex_setup_v1.0.0.exe)
  - [kuake](https://pan.quark.cn/s/6d094961e2c3)

- macos system (arm):

  - Method 1: Direct download: [Github](https://github.com/zstar1003/FreeTex/releases/download/v1.0.0/FreeTex-Installer-1.0.0.dmg)
  - Method 2: Install using Homebrew: `brew install freetex`

  > [!NOTE]
  > See [issue #44](https://github.com/zstar1003/FreeTex/issues/44) for the v1.0.0 macOS installer's `No module named 'openai'` issue and the maintainer's historical patch. That patch addresses missing dependencies; it does not imply inclusion of current source fixes.


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
## Current main source behavior (not a v1.0.0 installer guarantee)

The following describes `main` after [PR #52](https://github.com/zstar1003/FreeTex/pull/52), [PR #53](https://github.com/zstar1003/FreeTex/pull/53), [PR #54](https://github.com/zstar1003/FreeTex/pull/54) and [PR #55](https://github.com/zstar1003/FreeTex/pull/55). It does not automatically apply to the `win` branch or older releases.

This documentation review checked source, release asset metadata and the issue only. It did not directly install or validate the DMG/EXE, historical patch, signing or notarization. Merging source changes does not replace existing release assets or mean that a new complete installer has been published.

### Multimodal connection check

The **测试模型列表** (Test model list) button only requests `/models` from the configured service. It does not upload an image or run model inference. Success does not verify the selected model's vision capabilities; failure may only mean the service does not support listing models. Actual recognition sends the selected model and image to `/chat/completions` and must be verified separately.

The check runs in the background and ignores repeated clicks while pending. Network timeouts are set to 10 seconds with automatic retries disabled. Closing the dialog does not wait for the request or show its late result; an already-started read-only request finishes in the background and closes its client. This is a network-operation timeout, not a strict total-duration deadline. Exiting the entire application may still wait for outstanding pool tasks to finish.

### Recognition routing and failures

With multimodal recognition enabled, requests no longer require a successfully loaded local model. Provider errors or unreadable configuration are displayed as recognition failures, without silently switching to local inference, announcing success or enabling copying of error text. To use local recognition, disable multimodal recognition in settings. Local model initialization still follows the existing startup flow; this change does not skip startup loading or validate live provider compatibility.

### Settings storage and migration

Settings, including API keys, live in the current user profile instead of bundled `_MEIPASS` resources: `~/Library/Application Support/FreeTex/config.json` on macOS, `%APPDATA%/FreeTex/config.json` on Windows, and `$XDG_CONFIG_HOME/FreeTex/config.json` on Linux (default `~/.config`). Source runs use the same location.

On first read, the currently available legacy `config.json` is migrated without modifying the original. Existing user settings take precedence over new bundled defaults. Failed migration/parsing does not overwrite legacy data; failed saves do not truncate existing settings. Settings already lost with an old onefile temporary directory cannot be recovered.

This is local plaintext JSON, not a credential vault. New files have owner-only permissions (0600) on POSIX; Windows uses the profile directory access controls. Do not share configuration containing API keys. Tests use temporary directories and synthetic credentials only; signed packages and native cross-platform filesystems have not been validated.

Avoid editing settings from multiple FreeTex instances simultaneously (normal saves use an in-process lock). Filesystems without hard-link support may reject initial migration explicitly; the original remains intact.
