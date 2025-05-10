import os
import subprocess

# 使用Nuitka打包，花费半天时间，但打包后仍有问题，暂时搁置


def build_app():
    """使用Nuitka打包应用程序"""

    # 确保当前目录是项目根目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # 构建命令
    cmd = [
        "python",
        "-m",
        "nuitka",
        "--standalone",
        "--mingw64",
        "--show-progress",
        "--show-memory",
        "--plugin-enable=pyqt5",
        "--include-qt-plugins=all",
        "--include-package=unimernet",
        "--include-package=tools",
        "--include-package=resources",
        "--include-package=qfluentwidgets",
        "--include-data-dir=models=models",
        "--include-data-dir=libs=libs",
        "--include-data-dir=resources=resources",
        "--include-data-files=*.yaml=config",
        "--include-data-files=*.json=config",
        "--windows-icon-from-ico=resources/images/icon.ico",
        "--windows-company-name=FreeTex",
        "--windows-product-name=FreeTex",
        "--windows-file-version=0.2.0",
        "--windows-product-version=0.2.0",
        "--output-dir=dist",
        "main.py",
    ]

    # 执行命令
    subprocess.run(cmd, check=True)

    print("打包完成！输出目录: dist")


if __name__ == "__main__":
    build_app()
