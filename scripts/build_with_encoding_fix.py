#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建脚本，专门处理编码问题
"""

import os
import sys
import subprocess
import locale

def setup_encoding():
    """设置正确的编码环境"""
    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONPATH'] = os.pathsep.join([
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        os.environ.get('PYTHONPATH', '')
    ])
    
    # 设置控制台编码
    if sys.platform == 'win32':
        try:
            # 设置控制台为UTF-8
            subprocess.run(['chcp', '65001'], shell=True, check=False)
        except:
            pass
    
    # 设置locale
    try:
        locale.setlocale(locale.LC_ALL, '')
    except:
        pass

def build_with_pyinstaller():
    """使用PyInstaller打包应用程序"""
    
    # 设置编码
    setup_encoding()
    
    # 确保当前目录是项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    print(f"项目根目录: {project_root}")
    print(f"当前工作目录: {os.getcwd()}")
    
    # 构建命令
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "main.spec"
    ]
    
    print("开始构建...")
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        # 执行命令
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
        print("构建成功！")
        print(result.stdout)
        
        # 显示构建结果
        dist_path = os.path.join(project_root, "dist", "FreeTex")
        if os.path.exists(dist_path):
            print(f"构建完成！输出目录: {dist_path}")
            print("文件列表:")
            for root, dirs, files in os.walk(dist_path):
                level = root.replace(dist_path, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files[:10]:  # 只显示前10个文件
                    print(f"{subindent}{file}")
                if len(files) > 10:
                    print(f"{subindent}... 还有 {len(files) - 10} 个文件")
        else:
            print("警告: 构建目录不存在")
            
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        print(f"错误输出: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"构建过程中出现异常: {e}")
        sys.exit(1)

def test_encoding():
    """测试编码设置"""
    print("测试编码设置...")
    print(f"系统编码: {sys.getdefaultencoding()}")
    print(f"文件系统编码: {sys.getfilesystemencoding()}")
    print(f"PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING', 'Not set')}")
    
    # 测试路径处理
    test_path = "测试路径/test path/テスト"
    try:
        encoded = test_path.encode('utf-8').decode('utf-8')
        print(f"编码测试成功: {encoded}")
    except Exception as e:
        print(f"编码测试失败: {e}")

if __name__ == "__main__":
    print("FreeTex 构建脚本 - 编码修复版")
    print("=" * 50)
    
    # 测试编码
    test_encoding()
    print()
    
    # 构建应用
    build_with_pyinstaller() 