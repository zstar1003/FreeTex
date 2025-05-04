import sys
import os
import json
from PyQt5.QtCore import Qt, QTimer, QRect, QSize, QThread
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QKeySequence
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
    setTheme, Theme
)



class MainWindow(QMainWindow):
    """ 主窗口类 """
    def __init__(self):
        """
        初始化主窗口。
        设置窗口属性、布局和控件。
        """
        super().__init__()
        self.initWindow()
        
        # 加载配置文件
        self.config = self.load_config()
        
        # 创建中央部件
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        # 主布局
        self.mainLayout = QVBoxLayout(self.centralWidget)
        self.mainLayout.setContentsMargins(20, 20, 20, 20)
        self.mainLayout.setSpacing(15)

        # 初始化控件
        self.initWidgets()
        # 设置快捷键
        self.setup_shortcuts()
        
        # 初始化本地处理器
        self.processor_thread = QThread()
        self.local_processor = LocalProcessor("demo.yaml")
        self.local_processor.moveToThread(self.processor_thread)
        self.local_processor.finished.connect(self.on_recognition_finished)
        self.processor_thread.start()
        
        self.overlay = None # 用于存储截图覆盖层实例
        self.original_pixmap = None # 保存原始（未缩放）的截图或上传图片


    def initWindow(self):
        """
        初始化窗口设置
        """
        self.resize(800, 700)
        self.setWindowTitle('FreeTex - 免费的智能公式识别神器')

        icon_path = "images/icon.ico"
        self.setWindowIcon(QIcon(icon_path))

    def initWidgets(self):
        """
        初始化界面控件
        """
        # 图片显示区域
        self.imageCard = SimpleCardWidget(self.centralWidget)
        self.imageCard.setBorderRadius(8)
        
        self.imageLabel = ImageLabel("请上传图片或截图", self.imageCard)
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setScaledContents(False)
        self.imageLabel.setMinimumSize(800, 400)
        self.imageLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 使用居中对齐的布局
        imageLayout = QVBoxLayout(self.imageCard)
        imageLayout.setContentsMargins(0, 0, 0, 0)  # 完全移除内边距
        imageLayout.addWidget(self.imageLabel, 0, Qt.AlignCenter)  # 居中显示
        imageLayout.setSpacing(0)  # 移除内部间距


        # LaTeX 结果显示区域 - 使用 Fluent UI SimpleCardWidget 和 TextEdit
        self.latexCard = SimpleCardWidget(self.centralWidget)
        self.latexCard.setBorderRadius(8)

        self.latexEdit = TextEdit(self.latexCard) # Use TextEdit
        self.latexEdit.setPlaceholderText('识别出的 LaTeX 公式将显示在这里')
        self.latexEdit.setReadOnly(True)
        self.latexEdit.setMinimumHeight(100) # Set minimum height
        self.latexEdit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        latexLayout = QVBoxLayout(self.latexCard)
        latexLayout.addWidget(self.latexEdit)
        latexLayout.setContentsMargins(10, 10, 10, 10)

        # 底部按钮布局
        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(10)

        # 上传图片按钮 - 使用 Fluent UI PushButton
        self.uploadButton = FluentPushButton('上传图片', self.centralWidget)
        self.uploadButton.setIcon(FIF.PHOTO) # Use Fluent Icon
        self.uploadButton.clicked.connect(self.uploadImage)

        # 截图按钮 - 使用 Fluent UI PushButton
        self.screenshotButton = FluentPushButton('截图', self.centralWidget)
        self.screenshotButton.setIcon(FIF.CUT) # Use Fluent Icon
        self.screenshotButton.clicked.connect(self.start_screenshot_process)

        # 添加按钮到布局
        buttonLayout.addWidget(self.uploadButton)
        buttonLayout.addWidget(self.screenshotButton)
        buttonLayout.addStretch(1)

        # 将所有组件添加到主布局
        self.mainLayout.setContentsMargins(10, 10, 10, 10)  # 减少主布局边距
        self.mainLayout.setSpacing(10)
        self.mainLayout.addWidget(self.imageCard, 6)  # 图片区域分配更多空间
        self.mainLayout.addWidget(self.latexCard, 4)  # 结果区域分配较少空间
        self.mainLayout.addLayout(buttonLayout)


    def uploadImage(self):
        """
        上传图片功能。
        打开文件对话框让用户选择图片，并在界面上显示。
        """
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            ".", # Start directory
            "Image Files (*.png *.jpg *.bmp *.jpeg)"
        )
        if fileName:
            pixmap = QPixmap(fileName)
            if not pixmap.isNull():
                print(f"上传图片: {fileName}, 大小: {pixmap.size()}")
                # Use a timer to ensure the layout has settled before displaying the image
                QTimer.singleShot(100, lambda: self.display_result_pixmap(pixmap))
                # self.process_image(pixmap)
            else:
                print(f"无法加载图片: {fileName}")
                self.display_result_pixmap(QPixmap()) # Display empty pixmap
                self.latexEdit.setText('无法加载图片')


    def start_screenshot_process(self):
        """
        开始截图流程 - 确保主窗口完全隐藏后再显示截图覆盖层
        """
        print("开始截图流程...")
        self.hide()
        # 确保窗口完全隐藏后再显示覆盖层
        QTimer.singleShot(200, self.create_and_show_overlay)
        # 强制重绘和更新
        self.repaint()
        QApplication.processEvents()

    def create_and_show_overlay(self):
        """
        创建并显示截图覆盖层，确保覆盖层获得焦点
        """
        print("创建截图覆盖层...")
        if self.overlay:
            self.overlay.deleteLater()
            
        self.overlay = ScreenshotOverlay()
        self.overlay.screenshot_taken.connect(self.handle_screenshot_result)
        
        if self.overlay.full_screenshot is None:
            print("截图捕获失败")
            return
            
        print("显示截图覆盖层...")
        self.overlay.show()
        self.overlay.activateWindow()  # 确保覆盖层获得焦点
        self.overlay.raise_()  # 确保覆盖层在最上层


    def handle_screenshot_result(self, pixmap):
        """
        处理从 ScreenshotOverlay 返回的截图结果。
        """
        print(f"接收到截图结果. Pixmap valid: {not pixmap.isNull()}, Size: {pixmap.size()}")
        # Schedule display_result_pixmap and showing main window
        QTimer.singleShot(100, lambda: self.display_result_pixmap(pixmap))
        QTimer.singleShot(150, self.show_and_activate_main_window)

        if self.overlay:
             self.overlay = None # Clear reference


    def show_and_activate_main_window(self):
        """Helper to show and activate main window after a delay."""
        print("显示并激活主窗口...")
        self.show()
        self.activateWindow()


    def display_result_pixmap(self, pixmap):
        """
        显示接收到的截图或上传的图片结果，并进行缩放。
        Handles null/empty pixmaps gracefully. Fixes scaling issue.

        Args:
            pixmap (QPixmap): 要显示的图像 (可以是空的 QPixmap)。
        """
        print(f"display_result_pixmap called. Pixmap valid: {not pixmap.isNull()}, Size: {pixmap.size()}")

        if pixmap and not pixmap.isNull():
            print(f"显示图片，原始大小: {pixmap.size()}")
            self.original_pixmap = pixmap.copy() # Always store the received pixmap as the new original
            print(f"Stored original_pixmap size: {self.original_pixmap.size()}")

            self._scale_and_display_image()
            self.process_image(pixmap)
        else:
            print("显示图片：接收到无效或空图片。")
            self.latexEdit.setText("图片加载失败或取消")
            self.imageLabel.setText("图片加载失败或取消")

            self.original_pixmap = None
            self.imageLabel.setPixmap(QPixmap())
            self.imageLabel.setText("请上传图片或截图")


    def _scale_and_display_image(self):
        """
        根据 QLabel (ImageLabel) 的大小缩放并显示 self.original_pixmap。
        修改：确保图片在Label中完全居中显示
        """
        print("_scale_and_display_image called.")
        if not self.original_pixmap or self.original_pixmap.isNull():
            print("_scale_and_display_image: 无有效原始图片可显示，清空 QLabel。")
            self.imageLabel.setPixmap(QPixmap())
            self.imageLabel.setText("无图片")
            return

        # 获取Label的有效布局尺寸
        lbl_size = self.imageLabel.size()
        
        # 计算最大可用尺寸
        max_width = lbl_size.width()
        max_height = lbl_size.height()
        
        # 根据原始图片比例计算最佳显示尺寸
        original_size = self.original_pixmap.size()
        width_ratio = max_width / original_size.width()
        height_ratio = max_height / original_size.height()
        scale_factor = min(width_ratio, height_ratio)
        
        # 应用比例计算目标尺寸
        target_width = int(original_size.width() * scale_factor)
        target_height = int(original_size.height() * scale_factor)
        
        print(f"_scale_and_display_image: 原始大小={original_size}, 目标尺寸={target_width}x{target_height}")

        # 创建空白画布并居中绘制图片
        canvas = QPixmap(lbl_size)
        canvas.fill(Qt.transparent)
        
        painter = QPainter(canvas)
        scaled_pixmap = self.original_pixmap.scaled(
            target_width, 
            target_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # 计算居中位置
        x = (lbl_size.width() - scaled_pixmap.width()) // 2
        y = (lbl_size.height() - scaled_pixmap.height()) // 2
        
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
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # 如果配置文件不存在或格式错误，使用默认配置
            return {
                "shortcuts": {
                    "screenshot": "Ctrl+Alt+Q"
                }
            }

    def setup_shortcuts(self):
        """设置快捷键"""
        # 从配置读取所有快捷键
        shortcuts = self.config.get("shortcuts", {})
        
        # 截图快捷键
        shortcut = QShortcut(
            QKeySequence(shortcuts.get("screenshot", "Ctrl+Alt+Q")),
            self
        )
        shortcut.activated.connect(self.start_screenshot_process)

        # 上传图片快捷键
        upload_shortcut = QShortcut(
            QKeySequence(shortcuts.get("upload", "Ctrl+U")),
            self
        )
        upload_shortcut.activated.connect(self.uploadImage)

        # 初始化剪切板处理器
        self.clipboard_handler = ClipboardHandler(self)
        self.clipboard_handler.image_received.connect(self.handle_clipboard_image)
        
        # 粘贴快捷键
        self.paste_shortcut = QShortcut(
            QKeySequence(shortcuts.get("paste", "Ctrl+V")),
            self
        )
        self.paste_shortcut.activated.connect(self.clipboard_handler.handle_paste)

    def handle_clipboard_image(self, image):
        """处理从剪切板粘贴的图片"""
        pixmap = QPixmap.fromImage(image)
        if not pixmap.isNull():
            self.display_result_pixmap(pixmap)
        else:
            self.latexEdit.setText("剪切板中的图片无效")
    
    def process_image(self, pixmap: QPixmap):
        """异步处理图像"""
        if not pixmap or pixmap.isNull():
            print("无效的图片数据")  # 添加调试日志
            return
        try:
            print("开始处理图片...")  # 添加调试日志
            self.latexEdit.setText("正在识别图像...")
            # 直接调用处理器线程的方法
            self.local_processor.process_pixmap(pixmap)
        except Exception as e:
            print(f"图像处理错误: {e}")  # 添加详细的错误日志
            self.latexEdit.setText("图像处理发生错误")
                               
    def on_recognition_finished(self, result):
        """识别完成回调"""
        print(f"接收到识别结果: {result}") 
        self.latexEdit.setText(result)

    def closeEvent(self, event):
        """窗口关闭时清理线程"""
        self.processor_thread.quit()
        self.processor_thread.wait()
        super().closeEvent(event)

if __name__ == '__main__':
    # 启用高 DPI 支持 (如果开启，可能会影响多屏截图时的准确性)
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec_())