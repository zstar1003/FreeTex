import json
import logging
import os
import sys
from typing import List

import win32api
import win32con
from latex2mathml.converter import convert
from PyQt5.QtCore import (
    QFile,
    QIODevice,
    Qt,
    QTextStream,
    QThread,
    QTimer,
    QUrl,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QFont,
    QFontDatabase,
    QIcon,
    QImage,
    QKeySequence,
    QPainter,
    QPixmap,
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QShortcut,
    QSizePolicy,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

import resources  # noqa: F401
from qfluentwidgets import (
    ComboBox,
    ImageLabel,
    SimpleCardWidget,
    StateToolTip,
    TextEdit,
)
from qfluentwidgets import (
    FluentIcon as FIF,
)
from qfluentwidgets import (
    PushButton as FluentPushButton,
)
from tools.clipboard_handler import ClipboardHandler
from tools.local_processor import LocalProcessor

# 软件版本号常量
SOFTWARE_VERSION = "v0.3.0"


def render_latex_to_html(latex_code):
    """
    将 LaTeX 公式转换为 HTML 内容

    Args:
        latex_code: LaTeX 公式代码
    """
    try:
        fd = QFile(":/mathview.html")
        if fd.open(QIODevice.ReadOnly | QFile.Text):
            html = QTextStream(fd).readAll()
            return html.replace("{latex_code}", latex_code)
        else:
            raise FileNotFoundError("MathView HTML file not found")
    except Exception as e:
        logging.error(f"LaTeX 转换错误: {str(e)}")
        return f"<html><body>转换错误: {str(e)}</body></html>"


def resource_path(filename: str) -> str:
    if getattr(sys, "frozen", False):
        # Running in a PyInstaller bundle
        try:
            # 使用utf-8编码处理路径，避免编码问题
            base_path = sys._MEIPASS.encode('utf-8').decode('utf-8')
            return os.path.join(base_path, filename)
        except (UnicodeDecodeError, UnicodeEncodeError):
            # 如果编码出错，尝试使用原始路径
            return os.path.join(sys._MEIPASS, filename)
    else:
        # Running in normal Python environment
        return os.path.join(os.path.abspath("."), filename)


class ModelStatusWidget(QWidget):
    """模型状态指示器组件"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedHeight(30)

        # 创建水平布局
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setContentsMargins(5, 0, 5, 0)
        self.hBoxLayout.setSpacing(8)

        # 状态指示灯
        self.statusIndicator = QLabel(self)
        self.statusIndicator.setFixedSize(12, 12)
        self.statusIndicator.setStyleSheet("background-color: red; border-radius: 6px;")

        # 状态文本
        self.statusText = QLabel("模型正在加载中...", self)

        # 添加到布局
        self.hBoxLayout.addWidget(self.statusIndicator)
        self.hBoxLayout.addWidget(self.statusText)
        self.hBoxLayout.addStretch(1)

    def setLoaded(self, device_info=""):
        """设置模型已加载状态"""
        self.statusIndicator.setStyleSheet(
            "background-color: #2ecc71; border-radius: 6px;"
        )  # Green color
        self.statusText.setText("模型已加载完成")

    def setLoading(self):
        """设置模型加载中状态"""
        self.statusIndicator.setStyleSheet(
            "background-color: #e74c3c; border-radius: 6px;"
        )  # Red color
        self.statusText.setText("模型正在加载中...")

    def setLoadingFailed(self, error_info=""):
        """设置模型加载失败状态"""
        self.statusIndicator.setStyleSheet(
            "background-color: #f39c12; border-radius: 6px;"
        )  # Orange color
        self.statusText.setText(f"模型加载失败: {error_info}")


class MainWindow(QMainWindow):
    """主窗口类"""

    process_request = pyqtSignal(QPixmap)

    def __init__(self):
        """
        初始化主窗口。
        设置窗口属性、布局和控件。
        """
        super().__init__()

        # os.makedirs("logs", exist_ok=True)
        # 初始化日志
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                # logging.FileHandler("logs/FreeTex.log", encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger("FreeTex")

        # 设置窗口背景颜色
        self.setStyleSheet("background-color: #f0f4f9")
        # 加载配置文件
        self.config = self.load_config()

        # 使用resource_path函数获取正确的脚本目录
        if getattr(sys, "frozen", False):
            # 在打包后的应用中，使用sys._MEIPASS作为基础目录
            self.script_dir = sys._MEIPASS
        else:
            # 在开发环境中，使用__file__的目录
            self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.base_url = QUrl.fromLocalFile(self.script_dir + os.path.sep)
        self.logger.info(f"脚本目录: {self.script_dir}")
        self.logger.info(f"基础URL: {self.base_url.toString()}")

        # 创建中央部件
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        # 主布局
        self.mainLayout = QVBoxLayout(self.centralWidget)

        # 初始化控件 (包括ModelStatusWidget)
        self.initWidgets()

        # 设置快捷键
        self.setup_shortcuts()

        # 初始化本地处理器和线程
        self.processor_thread = QThread()
        # 创建LocalProcessor实例，此时不会加载模型
        # 使用resource_path函数获取正确的配置文件路径
        config_path = resource_path("demo.yaml")
        self.logger.info(f"使用配置文件路径: {config_path}")
        self.local_processor = LocalProcessor(config_path)
        # 将处理器移动到新线程
        self.local_processor.moveToThread(self.processor_thread)

        # 连接信号和槽
        # 1. 线程启动 -> 触发模型加载
        self.processor_thread.started.connect(self.local_processor.start_loading)
        # 2. 模型加载完成 -> 更新UI
        self.local_processor.model_loaded.connect(self.on_model_loading_finished)
        # 3. 识别完成 -> 更新结果文本
        self.local_processor.finished.connect(self.on_recognition_finished)
        # 4. 主线程请求处理图片 -> 触发处理器处理图片 (使用新信号)
        self.process_request.connect(self.local_processor.process_pixmap)

        # 启动处理器线程 (模型加载将在线程启动后自动触发)
        self.processor_thread.start()

        # 初始化窗口
        self.initWindow()
        # 初始化UI状态：模型加载中，禁用相关按钮
        self.modelStatus.setLoading()
        self.uploadButton.setEnabled(False)
        self.screenshotButton.setEnabled(False)

        self.overlay = None  # 用于存储截图覆盖层实例
        self.original_pixmap = None  # 保存原始（未缩放）的截图或上传图片

        # 初始化系统托盘
        self.init_tray()

        # 初始化剪贴板
        self.clipboard = QApplication.clipboard()

    def initWindow(self):
        """
        初始化窗口设置
        """
        self.resize(1000, 800)
        self.setWindowTitle("FreeTex - 免费的智能公式识别神器")

        icon_path = "resources/images/icon.ico"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.logger.warning(f"图标文件未找到: {icon_path}")

    def initWidgets(self):
        """
        初始化界面控件
        """
        # 状态栏和版本号区域
        statusBarWidget = QWidget(self.centralWidget)
        statusBarLayout = QHBoxLayout(statusBarWidget)
        statusBarLayout.setContentsMargins(5, 0, 5, 0)

        # 添加模型状态指示器
        self.modelStatus = ModelStatusWidget(statusBarWidget)

        # 添加版本号标签
        versionLabel = QLabel(SOFTWARE_VERSION, statusBarWidget)
        versionLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        versionLabel.setStyleSheet("color: black;")

        # 将组件添加到状态栏布局
        statusBarLayout.addWidget(self.modelStatus)
        statusBarLayout.addStretch(1)
        statusBarLayout.addWidget(versionLabel)

        # 图片显示区域
        self.imageCard = SimpleCardWidget(self.centralWidget)
        self.imageCard.setBorderRadius(8)

        self.imageLabel = ImageLabel("请上传图片或截图", self.imageCard)
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setScaledContents(False)
        self.imageLabel.setMinimumSize(500, 300)
        self.imageLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.imageLabel.setStyleSheet("background-color: #fafbfd;")

        imageLayout = QVBoxLayout(self.imageCard)
        imageLayout.setContentsMargins(0, 0, 0, 0)
        imageLayout.addWidget(self.imageLabel, 0, Qt.AlignCenter)
        imageLayout.setSpacing(0)

        # LaTeX 结果显示区域
        self.latexCard = SimpleCardWidget(self.centralWidget)
        self.latexCard.setBorderRadius(8)

        # 添加 LaTeX 渲染窗口
        self.renderCard = SimpleCardWidget(self.latexCard)
        self.renderCard.setBorderRadius(4)
        self.renderCard.setStyleSheet("background-color: white;")
        self.renderCard.setMinimumHeight(200)

        # 渲染标签
        self.renderView = QWebEngineView(self.renderCard)
        self.renderView.setMinimumHeight(150)
        self.renderView.setHtml(
            "<html><body><center>识别结果将显示在这里</center></body></html>",
            baseUrl=self.base_url,
        )
        self.renderView.setStyleSheet("border: none;")

        renderLayout = QVBoxLayout(self.renderCard)
        renderLayout.setContentsMargins(10, 10, 10, 10)
        renderLayout.addWidget(self.renderView)

        self.latexEdit = TextEdit(self.latexCard)
        self.latexEdit.setPlaceholderText("识别出的 LaTeX 公式将显示在这里")
        self.latexEdit.setReadOnly(True)
        self.latexEdit.setMinimumHeight(100)
        self.latexEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        latexLayout = QVBoxLayout(self.latexCard)
        latexLayout.addWidget(self.renderCard)
        latexLayout.addWidget(self.latexEdit)
        latexLayout.setContentsMargins(10, 10, 10, 10)
        latexLayout.setSpacing(10)

        # 底部按钮布局
        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(10)

        # 上传图片按钮
        self.uploadButton = FluentPushButton("上传图片", self.centralWidget)
        self.uploadButton.setIcon(FIF.PHOTO)
        self.uploadButton.clicked.connect(self.uploadImage)

        # 截图按钮
        self.screenshotButton = FluentPushButton("截图", self.centralWidget)
        self.screenshotButton.setIcon(FIF.CUT)
        self.screenshotButton.clicked.connect(self.start_screenshot_process)

        # 复制识别结果(Latex) 按钮
        self.copyButton = FluentPushButton("复制识别结果(Latex)", self.centralWidget)
        self.copyButton.setIcon(FIF.COPY)  # 使用复制图标
        self.copyButton.clicked.connect(self.copy_latex_result)
        self.copyButton.setEnabled(False)  # 初始禁用

        # 复制识别结果(Word/MathML) 按钮
        self.copyWordButton = FluentPushButton("复制识别结果(Word)", self.centralWidget)
        self.copyWordButton.setIcon(FIF.DOCUMENT)  # 使用文档图标
        self.copyWordButton.clicked.connect(self.copy_mathml_result)
        self.copyWordButton.setEnabled(False)  # 初始禁用

        # 添加LaTeX导出选项
        self.exportOptionsLayout = QHBoxLayout()
        self.exportOptionsLayout.setAlignment(Qt.AlignRight)

        self.exportLabel = QLabel("LaTeX导出格式：")
        self.exportComboBox = ComboBox(self)
        self.exportComboBox.addItems(["不加包裹", "$$包裹", "\\begin{equation}包裹"])
        self.exportComboBox.setCurrentIndex(0)
        self.exportComboBox.setFixedWidth(200)
        self.exportComboBox.currentIndexChanged.connect(self.onExportFormatChanged)

        self.exportOptionsLayout.addWidget(self.exportLabel)
        self.exportOptionsLayout.addWidget(self.exportComboBox)

        # 添加按钮到布局
        buttonLayout.addWidget(self.uploadButton)
        buttonLayout.addWidget(self.screenshotButton)
        buttonLayout.addWidget(self.copyWordButton)
        buttonLayout.addWidget(self.copyButton)
        buttonLayout.addStretch(1)
        buttonLayout.addLayout(self.exportOptionsLayout)

        # 将所有组件添加到主布局
        self.mainLayout.setContentsMargins(10, 10, 10, 10)
        self.mainLayout.setSpacing(10)
        self.mainLayout.addWidget(statusBarWidget)
        self.mainLayout.addWidget(self.imageCard, 6)
        self.mainLayout.addWidget(self.latexCard, 4)
        self.mainLayout.addLayout(buttonLayout)

        self.latexEdit.textChanged.connect(self.update_copy_button_state)

    def onExportFormatChanged(self, index):
        """
        当导出格式改变时调用

        Args:
            index: 选择的格式索引
        """
        self.logger.info(f"LaTeX导出格式已更改为: {self.exportComboBox.currentText()}")

    def on_model_loading_finished(self, device_info):
        """模型加载完成后的回调函数"""
        self.logger.info(f"接收到model_loaded信号. 设备: {device_info}")
        if "失败" in device_info:
            self.modelStatus.setLoadingFailed(device_info)
            self.uploadButton.setEnabled(False)
            self.screenshotButton.setEnabled(False)
            tooltip_text = f"模型加载失败: {device_info}"
            tooltip_state = False
        else:
            self.modelStatus.setLoaded(device_info)
            self.uploadButton.setEnabled(True)
            self.screenshotButton.setEnabled(True)
            self.copyButton.setEnabled(True)
            tooltip_text = f"模型加载完成: {device_info}"
            tooltip_state = True

        self.update_copy_button_state()
        # 显示提示
        tooltip = StateToolTip("模型状态", tooltip_text, self)
        tooltip.setState(tooltip_state)
        tooltip.show()
        tooltip.move(self.width() - tooltip.width() - 20, 20)

    def uploadImage(self):
        """
        上传图片功能。
        打开文件对话框让用户选择图片，并在界面上显示。
        """
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            ".",
            "Image Files (*.png *.jpg *.bmp *.jpeg);;All Files (*)",
        )
        if fileName:
            pixmap = QPixmap(fileName)
            if not pixmap.isNull():
                self.logger.info(f"上传图片: {fileName}, 大小: {pixmap.size()}")
                QTimer.singleShot(100, lambda: self.display_result_pixmap(pixmap))
            else:
                self.logger.error(f"无法加载图片: {fileName}")
                self.display_result_pixmap(QPixmap())
                self.latexEdit.setText("错误：无法加载图片")
                self.imageLabel.setText("错误：无法加载图片")

    def start_screenshot_process(self):
        """
        触发Windows自带的截图功能(Win+Shift+S)
        """
        self.logger.info("触发Windows截图...")
        # 确保剪贴板变化信号已连接
        clipboard = QApplication.clipboard()
        clipboard.dataChanged.connect(self.on_clipboard_change)
        
        # 模拟按下Win+Shift+S快捷键
        win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)  # Win键按下
        win32api.keybd_event(win32con.VK_LSHIFT, 0, 0, 0)  # Shift键按下
        win32api.keybd_event(0x53, 0, 0, 0)  # S键按下
        
        win32api.keybd_event(0x53, 0, win32con.KEYEVENTF_KEYUP, 0)  # S键释放
        win32api.keybd_event(win32con.VK_LSHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)  # Shift键释放
        win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)  # Win键释放
        
        # 显示提示
        tooltip = StateToolTip("截图提示", "请使用Windows截图工具选择区域", self)
        tooltip.setState(True)
        tooltip.show()
        tooltip.move(self.width() - tooltip.width() - 20, 20)

    def on_clipboard_change(self):
        """
        剪贴板内容变化的回调函数
        """
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasImage():
            image = clipboard.image()
            if not image.isNull():
                self.logger.info("检测到新的截图")
                # 断开信号连接，避免重复处理
                clipboard.dataChanged.disconnect(self.on_clipboard_change)
                self.handle_clipboard_image(image)

    def display_result_pixmap(self, pixmap):
        """
        显示接收到的截图或上传的图片结果，并进行缩放

        参数:
            pixmap (QPixmap): 要显示的图像
        """
        self.logger.debug(
            f"display_result_pixmap调用. 图片有效: {not pixmap.isNull()}, 大小: {pixmap.size()}"
        )

        if pixmap and not pixmap.isNull():
            self.logger.info(f"显示图片，原始大小: {pixmap.size()}")
            self.original_pixmap = pixmap.copy()
            self.logger.debug(f"存储原始图片大小: {self.original_pixmap.size()}")

            self._scale_and_display_image()
            if self.local_processor.model is not None:
                self.latexEdit.setText("正在识别图像...")
                self.process_request.emit(pixmap)
            else:
                self.latexEdit.setText("模型尚未加载，请稍候...")
                self.logger.warning("无法处理图片: 模型尚未加载完成")

        else:
            self.logger.warning("显示图片: 接收到无效或空图片")
            self.latexEdit.setText("图片加载失败或取消")
            self.imageLabel.setText("图片加载失败或取消")
            self.original_pixmap = None
            self.imageLabel.setPixmap(QPixmap())
            self.imageLabel.setText("请上传图片或截图")
            self.latexEdit.setPlaceholderText("识别出的 LaTeX 公式将显示在这里")

    def _scale_and_display_image(self):
        """
        根据QLabel大小缩放并显示图片，保持居中显示
        """
        if not self.original_pixmap or self.original_pixmap.isNull():
            self.imageLabel.setPixmap(QPixmap())
            return

        lbl_rect = self.imageLabel.contentsRect()
        max_width = lbl_rect.width()
        max_height = lbl_rect.height()

        if max_width <= 0 or max_height <= 0:
            self.logger.warning(
                f"_scale_and_display_image: 标签尺寸无效: {max_width}x{max_height}"
            )
            return

        scaled_pixmap = self.original_pixmap.scaled(
            max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        canvas = QPixmap(lbl_rect.size())
        canvas.fill(Qt.transparent)

        painter = QPainter(canvas)
        x = (canvas.width() - scaled_pixmap.width()) // 2
        y = (canvas.height() - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()

        self.imageLabel.setPixmap(canvas)
        self.imageLabel.setText("")

    def resizeEvent(self, event):
        """
        窗口大小改变事件，重新缩放图片以适应新的 QLabel 大小。
        """
        super().resizeEvent(event)
        if self.original_pixmap and not self.original_pixmap.isNull():
            QTimer.singleShot(0, self._scale_and_display_image)

    def load_config(self):
        """加载配置文件"""
        try:
            # 使用resource_path函数获取正确的配置文件路径
            config_path = resource_path("config.json")
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.logger.info("配置文件加载成功")
                return config
        except FileNotFoundError:
            self.logger.warning("配置文件未找到")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件解析错误: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"配置文件加载异常: {e}")
            return {}

    def setup_shortcuts(self):
        """设置快捷键"""
        # 从配置读取所有快捷键
        shortcuts = self.config.get("shortcuts", {})
        self.logger.info(f"从配置加载快捷键: {shortcuts}")

        # 截图快捷键
        screenshot_seq = shortcuts.get("screenshot", "Ctrl+Alt+Q")
        self.logger.debug(f"截图快捷键: {screenshot_seq}")
        self.shortcut_screenshot = QShortcut(QKeySequence(screenshot_seq), self)
        self.shortcut_screenshot.setEnabled(True)
        self.shortcut_screenshot.activated.connect(self.start_screenshot_process)

        # 上传图片快捷键
        upload_seq = shortcuts.get("upload", "Ctrl+U")
        self.logger.debug(f"上传图片快捷键: {upload_seq}")
        self.shortcut_upload = QShortcut(QKeySequence(upload_seq), self)
        self.shortcut_upload.setEnabled(True)
        self.shortcut_upload.activated.connect(self.uploadImage)

        # 初始化剪切板处理器
        self.clipboard_handler = ClipboardHandler(self)
        self.clipboard_handler.image_received.connect(self.handle_clipboard_image)

        # 粘贴快捷键
        paste_seq = shortcuts.get("paste", "Ctrl+V")
        self.logger.debug(f"粘贴快捷键: {paste_seq}")
        self.shortcut_paste = QShortcut(QKeySequence(paste_seq), self)
        self.shortcut_paste.setEnabled(True)
        self.shortcut_paste.activated.connect(self.clipboard_handler.handle_paste)

    def handle_clipboard_image(self, image: QImage):
        """处理从剪切板粘贴的图片 (QImage)"""
        self.logger.info(f"从剪切板接收到图片. 格式: {image.format()}")
        pixmap = QPixmap.fromImage(image)
        if not pixmap.isNull():
            self.display_result_pixmap(pixmap)
        else:
            self.logger.warning("剪切板中的图片无效")
            self.latexEdit.setText("剪切板中的图片无效")
            self.imageLabel.setText("剪切板中的图片无效")

    def on_recognition_finished(self, result):
        """识别完成后的回调函数"""
        self.logger.info(f"接收到识别结果: {result}")

        # 更新 LaTeX 文本框
        self.latexEdit.setText(result)

        # 更新渲染窗口
        try:
            # 使用 QWebEngineView 渲染公式
            html_content = render_latex_to_html(result)
            self.renderView.setHtml(html_content, baseUrl=self.base_url)
        except Exception as e:
            self.logger.error(f"渲染 LaTeX 公式时出错: {e}")
            self.renderView.setHtml(
                "<html><body><center>无法渲染当前公式</center></body></html>"
            )

        # 启用复制按钮
        self.copyButton.setEnabled(True)
        self.copyWordButton.setEnabled(True)

        # 显示提示
        tooltip = StateToolTip("识别完成", "公式已成功识别并转换为LaTeX格式", self)
        tooltip.setState(True)
        tooltip.move(self.width() - tooltip.width() - 10, 10)
        tooltip.show()

        # 更新复制按钮状态
        self.update_copy_button_state()

        # 保存当前的LaTeX代码
        self.current_latex = result

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        if self.tray_icon.isVisible():
            event.ignore()  # 忽略关闭事件
            self.hide()  # 隐藏主窗口
            self.tray_icon.showMessage(
                "FreeTex",
                "程序已最小化到系统托盘，双击图标可以重新打开窗口",
                QSystemTrayIcon.Information,
                2000,
            )
        else:
            # 如果托盘图标不可见，则正常关闭
            self.logger.info("正在关闭主窗口，停止处理器线程...")
            self.processor_thread.quit()
            self.processor_thread.wait(5000)
            if self.processor_thread.isRunning():
                self.logger.warning("处理器线程未正常终止")
            else:
                self.logger.info("处理器线程已停止")

            self.tray_icon.hide()  # 确保托盘图标被移除
            event.accept()

    def copy_latex_result(self):
        """将识别出的LaTeX结果复制到剪贴板"""
        latex_text = self.latexEdit.toPlainText()
        if latex_text:
            clipboard = QApplication.clipboard()
            export_format = self.exportComboBox.currentIndex()
            # 根据选择的格式添加包裹
            if export_format == 1:  # $$包裹
                formatted_latex = f"${latex_text}$"
            elif export_format == 2:  # \begin{equation}\end{equation}包裹
                formatted_latex = (
                    f"\\begin{{equation}}\n{latex_text}\n\\end{{equation}}"
                )
            else:  # 不加包裹
                formatted_latex = latex_text
            clipboard.setText(formatted_latex)
            self.logger.info("LaTeX结果已复制到剪贴板")
            tooltip = StateToolTip("复制成功", "LaTeX 代码已复制到剪贴板", self)
            tooltip.setState(True)
            tooltip.show()
            tooltip.move(self.width() - tooltip.width() - 20, 20)
        else:
            self.logger.warning("没有可复制的LaTeX结果")
            tooltip = StateToolTip("无结果", "没有可复制的LaTeX代码", self)
            tooltip.setState(False)
            tooltip.show()
            tooltip.move(self.width() - tooltip.width() - 20, 20)

    def copy_mathml_result(self):
        """将识别出的LaTeX结果转换为MathML并复制到剪贴板"""
        latex_text = self.latexEdit.toPlainText().strip()
        is_placeholder_or_empty = (not latex_text) or (
            latex_text == self.latexEdit.placeholderText().strip()
        )
        is_error_message = latex_text.startswith("识别失败:")

        if not is_placeholder_or_empty and not is_error_message:
            try:
                mathml_text = convert(latex_text)
                self.logger.debug(f"转换LaTeX到MathML:\n{mathml_text[:200]}...")
                clipboard = QApplication.clipboard()
                clipboard.setText(mathml_text)
                self.logger.info("MathML结果已复制到剪贴板")
                tooltip = StateToolTip(
                    "复制成功", "MathML 代码已复制到剪贴板，可粘贴到Word", self
                )
                tooltip.setState(True)
                tooltip.show()
                tooltip.move(self.width() - tooltip.width() - 20, 20)
            except Exception as e:
                error_msg = f"MathML转换失败: {str(e)}"
                self.logger.error(error_msg)
                tooltip = StateToolTip("复制失败", error_msg, self)
                tooltip.setState(False)
                tooltip.show()
                tooltip.move(self.width() - tooltip.width() - 20, 20)
        else:
            self.logger.warning("没有有效的LaTeX结果可转换")
            tooltip = StateToolTip("无结果", "没有可复制的LaTeX代码", self)
            tooltip.setState(False)
            tooltip.show()
            tooltip.move(self.width() - tooltip.width() - 20, 20)

    def update_copy_button_state(self):
        """根据latexEdit的内容启用/禁用复制按钮"""
        # 获取当前文本，忽略前后空白
        text = self.latexEdit.toPlainText().strip()
        # 如果文本非空，且不等于占位符文本，则启用按钮
        is_placeholder_or_empty = (not text) or (
            text == self.latexEdit.placeholderText().strip()
        )
        is_error_message = text.startswith("识别失败:")
        # 只有当文本非空、非占位符且不是错误信息时才启用复制按钮
        should_enable = not is_placeholder_or_empty and not is_error_message

        self.copyButton.setEnabled(should_enable)
        self.copyWordButton.setEnabled(should_enable)

    def init_tray(self):
        """初始化系统托盘"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())

        # 创建托盘菜单
        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示主窗口")
        show_action.triggered.connect(self.show_from_tray)
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self.quit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

        # 显示提示信息
        self.tray_icon.setToolTip("FreeTex - 智能公式识别神器")
        self.tray_icon.showMessage(
            "FreeTex",
            "程序已最小化到系统托盘，双击图标可以重新打开窗口",
            QSystemTrayIcon.Information,
            2000,
        )

    def show_from_tray(self):
        """从托盘显示窗口"""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def tray_icon_activated(self, reason):
        """托盘图标被激活时的处理函数"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_from_tray()

    def quit_app(self):
        """完全退出应用程序"""
        self.tray_icon.hide()
        QApplication.quit()


class App(QApplication):
    def __init__(self, argv: List[str]) -> None:
        super().__init__(argv)

        self.init_cwd()
        self.init_font()
        self.init_window()

    def init_cwd(self):
        if getattr(sys, "frozen", False):
            # Running in a PyInstaller bundle
            # 设置环境变量以确保正确的路径处理
            try:
                # 确保PYTHONIOENCODING设置为utf-8
                os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
                # 记录当前工作目录和资源目录
                cwd = os.getcwd()
                resource_dir = sys._MEIPASS
                self.logger.info(f"当前工作目录: {cwd}")
                self.logger.info(f"资源目录: {resource_dir}")
            except Exception as e:
                self.logger.warning(f"初始化工作目录时出现警告: {e}")
        else:
            # Running in normal Python environment
            pass

    def init_font(self):
        self.font_database = QFontDatabase()

        def _load_font(font_db: QFontDatabase, font_path: str, *args) -> QFont:
            try:
                font_id = font_db.addApplicationFont(font_path)
                if font_id == -1:
                    raise RuntimeError(f"Failed to load font: {font_path}")
                return QFont(font_db.applicationFontFamilies(font_id)[0], *args)
            except Exception as e:
                logging.warning(f"字体加载失败: {font_path}, 错误: {e}")
                # 返回系统默认字体
                return QFont()

        try:
            # 使用正确的字体文件
            crimson_pro_path = resource_path("resources/fonts/Crimson_Pro/CrimsonPro-VariableFont_wght.ttf")
            noto_serif_path = resource_path("resources/fonts/Noto_Serif_SC/NotoSerifSC-VariableFont_wght_3500_punc.ttf")
            
            self._fontIdCrimsonPro = _load_font(self.font_database, crimson_pro_path)
            self._fontIdNotoSerifSC = _load_font(self.font_database, noto_serif_path)
            
            self.setStyleSheet(
                '* { font-family: "Crimson Pro", "Noto Serif CJK SC"; color: black; }'
            )
        except Exception as e:
            logging.warning(f"字体初始化失败: {e}")
            # 使用系统默认字体
            self.setStyleSheet('* { color: black; }')

    def init_window(self):
        self._main_window = MainWindow()

    def run(self):
        self._main_window.show()


if __name__ == "__main__":
    # 启用高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough) # Optional policy
    app = App(sys.argv)
    app.run()
    sys.exit(app.exec_())