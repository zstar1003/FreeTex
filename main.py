import sys
import os
import json
import logging
from latex2mathml.converter import convert
from PyQt5.QtCore import Qt, QTimer, QRect, QSize, QThread, pyqtSignal, QMetaObject, Q_ARG, QPoint
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QKeySequence, QColor, QImage
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout,
                             QWidget, QFileDialog, QHBoxLayout, QSizePolicy)
from PyQt5.QtWidgets import QShortcut
from tools.screenshot import ScreenshotOverlay
from tools.clipboard_handler import ClipboardHandler
from tools.local_processor import LocalProcessor

from qfluentwidgets import (
    PushButton as FluentPushButton,
    FluentIcon as FIF,
    SimpleCardWidget,
    ImageLabel,
    TextEdit,
    setTheme, Theme,
    StateToolTip
)

# 软件版本号常量
SOFTWARE_VERSION = "v0.1.0"

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
        self.statusIndicator.setStyleSheet("background-color: #2ecc71; border-radius: 6px;") # Green color
        self.statusText.setText(f"模型已加载完成 ({device_info})")

    def setLoading(self):
        """设置模型加载中状态"""
        self.statusIndicator.setStyleSheet("background-color: #e74c3c; border-radius: 6px;") # Red color
        self.statusText.setText("模型正在加载中...")

    def setLoadingFailed(self, error_info=""):
        """设置模型加载失败状态"""
        self.statusIndicator.setStyleSheet("background-color: #f39c12; border-radius: 6px;") # Orange color
        self.statusText.setText(f"模型加载失败: {error_info}")


class MainWindow(QMainWindow):
    """ 主窗口类 """
    process_request = pyqtSignal(QPixmap)

    def __init__(self):
        """
        初始化主窗口。
        设置窗口属性、布局和控件。
        """
        super().__init__()
        self.initWindow()

        os.makedirs('logs', exist_ok=True)
        # 初始化日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/FreeTex.log', encoding='utf-8'), 
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('FreeTex')
        
        # 设置窗口背景颜色
        self.setStyleSheet("background-color: #f0f4f9;")
        # 加载配置文件
        self.config = self.load_config()

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
        self.local_processor = LocalProcessor("demo.yaml")
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

        # 初始化UI状态：模型加载中，禁用相关按钮
        self.modelStatus.setLoading()
        self.uploadButton.setEnabled(False)
        self.screenshotButton.setEnabled(False)

        self.overlay = None # 用于存储截图覆盖层实例
        self.original_pixmap = None # 保存原始（未缩放）的截图或上传图片


    def initWindow(self):
        """
        初始化窗口设置
        """
        self.resize(800, 700)
        self.setWindowTitle('FreeTex - 免费的智能公式识别神器')

        icon_path = "images/icon.ico"
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

        self.latexEdit = TextEdit(self.latexCard)
        self.latexEdit.setPlaceholderText('识别出的 LaTeX 公式将显示在这里')
        self.latexEdit.setReadOnly(True)
        self.latexEdit.setMinimumHeight(100)
        self.latexEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        latexLayout = QVBoxLayout(self.latexCard)
        latexLayout.addWidget(self.latexEdit)
        latexLayout.setContentsMargins(10, 10, 10, 10)

        # 底部按钮布局
        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(10)

        # 上传图片按钮
        self.uploadButton = FluentPushButton('上传图片', self.centralWidget)
        self.uploadButton.setIcon(FIF.PHOTO)
        self.uploadButton.clicked.connect(self.uploadImage)

        # 截图按钮
        self.screenshotButton = FluentPushButton('截图', self.centralWidget)
        self.screenshotButton.setIcon(FIF.CUT)
        self.screenshotButton.clicked.connect(self.start_screenshot_process)
        
        # 复制识别结果(Latex) 按钮
        self.copyButton = FluentPushButton('复制识别结果(Latex)', self.centralWidget)
        self.copyButton.setIcon(FIF.COPY) # 使用复制图标
        self.copyButton.clicked.connect(self.copy_latex_result)
        self.copyButton.setEnabled(False) # 初始禁用

        # 复制识别结果(Word/MathML) 按钮
        self.copyWordButton = FluentPushButton('复制识别结果(Word)', self.centralWidget)
        self.copyWordButton.setIcon(FIF.DOCUMENT) # 使用文档图标
        self.copyWordButton.clicked.connect(self.copy_mathml_result)
        self.copyWordButton.setEnabled(False) # 初始禁用
        
        # 添加按钮到布局
        buttonLayout.addWidget(self.uploadButton)
        buttonLayout.addWidget(self.screenshotButton)
        buttonLayout.addWidget(self.copyButton)
        buttonLayout.addWidget(self.copyWordButton)
        buttonLayout.addStretch(1) 

        # 将所有组件添加到主布局
        self.mainLayout.setContentsMargins(10, 10, 10, 10)
        self.mainLayout.setSpacing(10)
        self.mainLayout.addWidget(statusBarWidget)
        self.mainLayout.addWidget(self.imageCard, 6) 
        self.mainLayout.addWidget(self.latexCard, 4)
        self.mainLayout.addLayout(buttonLayout)

        self.latexEdit.textChanged.connect(self.update_copy_button_state)
        
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
            "Image Files (*.png *.jpg *.bmp *.jpeg);;All Files (*)"
        )
        if fileName:
            pixmap = QPixmap(fileName)
            if not pixmap.isNull():
                self.logger.info(f"上传图片: {fileName}, 大小: {pixmap.size()}")
                QTimer.singleShot(100, lambda: self.display_result_pixmap(pixmap))
            else:
                self.logger.error(f"无法加载图片: {fileName}")
                self.display_result_pixmap(QPixmap())
                self.latexEdit.setText('错误：无法加载图片')
                self.imageLabel.setText("错误：无法加载图片")


    def start_screenshot_process(self):
        """
        开始截图流程 - 确保主窗口完全隐藏后再显示截图覆盖层
        """
        self.logger.info("开始截图流程...")
        self.hide()
        QTimer.singleShot(200, self.create_and_show_overlay)


    def create_and_show_overlay(self):
        """
        创建并显示截图覆盖层，确保覆盖层获得焦点
        """
        self.logger.info("创建截图覆盖层...")
        if self.overlay is not None:
            self.overlay.deleteLater()
            self.overlay = None

        self.overlay = ScreenshotOverlay()
        self.overlay.screenshot_taken.connect(self.handle_screenshot_result)
        self.overlay.screenshot_cancelled.connect(self.handle_screenshot_cancelled)

        if self.overlay.full_screenshot is None:
            self.logger.warning("截图捕获失败或取消")
            self.show_and_activate_main_window()
            self.imageLabel.setText("截图失败或取消")
            self.latexEdit.setText("截图失败或取消")
            self.overlay = None
            return

        self.logger.info("显示截图覆盖层...")
        self.overlay.show()
        self.overlay.activateWindow()
        self.overlay.raise_()

    def handle_screenshot_cancelled(self):
        """处理截图取消事件"""
        self.logger.info("截图已取消")
        self.show_and_activate_main_window()
        self.imageLabel.setText("截图已取消")
        self.latexEdit.setText("截图已取消")
        if self.overlay:
            self.overlay.deleteLater()
            self.overlay = None

    def handle_screenshot_result(self, pixmap):
        """
        处理从ScreenshotOverlay返回的截图结果
        """
        self.logger.info(f"接收到截图结果. 图片有效: {not pixmap.isNull()}, 大小: {pixmap.size()}")
        QTimer.singleShot(100, self.show_and_activate_main_window)
        QTimer.singleShot(150, lambda: self.display_result_pixmap(pixmap))

        if self.overlay:
            pass

    def show_and_activate_main_window(self):
        """显示并激活主窗口"""
        self.logger.info("显示并激活主窗口...")
        if self.overlay and self.overlay.isVisible():
            self.overlay.hide()

        self.showNormal()
        self.activateWindow()
        self.raise_()

    def display_result_pixmap(self, pixmap):
        """
        显示接收到的截图或上传的图片结果，并进行缩放
        
        参数:
            pixmap (QPixmap): 要显示的图像
        """
        self.logger.debug(f"display_result_pixmap调用. 图片有效: {not pixmap.isNull()}, 大小: {pixmap.size()}")

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
            self.latexEdit.setPlaceholderText('识别出的 LaTeX 公式将显示在这里')

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
            self.logger.warning(f"_scale_and_display_image: 标签尺寸无效: {max_width}x{max_height}")
            return

        scaled_pixmap = self.original_pixmap.scaled(
            max_width,
            max_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
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
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.logger.info("配置文件加载成功")
                return config
        except FileNotFoundError:
            self.logger.warning("配置文件未找到")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件解析错误: {e}")
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
        """识别完成回调"""
        self.logger.info(f"接收到识别结果:\n{result[:100]}...")
        self.latexEdit.setText(result)

    def closeEvent(self, event):
        """窗口关闭时清理线程"""
        self.logger.info("正在关闭主窗口，停止处理器线程...")
        self.processor_thread.quit()
        self.processor_thread.wait(5000)
        if self.processor_thread.isRunning():
            self.logger.warning("处理器线程未正常终止")
        else:
            self.logger.info("处理器线程已停止")

        if self.overlay is not None and self.overlay.isVisible():
            self.overlay.close()
            self.overlay = None

        super().closeEvent(event)
    
    def copy_latex_result(self):
        """将识别出的LaTeX结果复制到剪贴板"""
        latex_text = self.latexEdit.toPlainText()
        if latex_text:
            clipboard = QApplication.clipboard()
            clipboard.setText(latex_text)
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
        is_placeholder_or_empty = (not latex_text) or (latex_text == self.latexEdit.placeholderText().strip())
        is_error_message = latex_text.startswith("识别失败:")

        if not is_placeholder_or_empty and not is_error_message:
            try:
                mathml_text = convert(latex_text)
                self.logger.debug(f"转换LaTeX到MathML:\n{mathml_text[:200]}...")
                clipboard = QApplication.clipboard()
                clipboard.setText(mathml_text)
                self.logger.info("MathML结果已复制到剪贴板")
                tooltip = StateToolTip("复制成功", "MathML 代码已复制到剪贴板，可粘贴到Word", self)
                tooltip.setState(True)
                button_center_global = self.copyWordButton.mapToGlobal(QPoint(self.copyWordButton.width() // 2, self.copyWordButton.height() // 2))
                tooltip.show()
                tooltip.move(self.width() - tooltip.width() - 20, 20)
            except Exception as e:
                error_msg = f"MathML转换失败: {str(e)}"
                self.logger.error(error_msg)
                tooltip = StateToolTip("复制失败", error_msg, self)
                tooltip.setState(False)
                button_center_global = self.copyWordButton.mapToGlobal(QPoint(self.copyWordButton.width() // 2, self.copyWordButton.height() // 2))
                tooltip.show()
                tooltip.move(self.width() - tooltip.width() - 20, 20)
        else:
            self.logger.warning("没有有效的LaTeX结果可转换")
            tooltip = StateToolTip("无结果", "没有可复制的LaTeX代码", self)
            tooltip.setState(False)
            button_center_global = self.copyWordButton.mapToGlobal(QPoint(self.copyWordButton.width() // 2, self.copyWordButton.height() // 2))
            tooltip.show()
            tooltip.move(self.width() - tooltip.width() - 20, 20)


    def update_copy_button_state(self):
        """根据latexEdit的内容启用/禁用复制按钮"""
        # 获取当前文本，忽略前后空白
        text = self.latexEdit.toPlainText().strip()
        # 如果文本非空，且不等于占位符文本，则启用按钮
        is_placeholder_or_empty = (not text) or (text == self.latexEdit.placeholderText().strip())
        is_error_message = text.startswith("识别失败:")
        # 只有当文本非空、非占位符且不是错误信息时才启用复制按钮
        should_enable = not is_placeholder_or_empty and not is_error_message

        self.copyButton.setEnabled(should_enable)
        self.copyWordButton.setEnabled(should_enable)



if __name__ == '__main__':
    # 启用高 DPI 支持 (如果开启，可能会影响多屏截图时的准确性)
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    # QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough) # Optional policy

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec_())