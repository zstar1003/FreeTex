import sys
import os
import json
from PyQt5.QtCore import Qt, QTimer, QRect, QSize, QThread, pyqtSignal, QMetaObject, Q_ARG, QPoint
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QKeySequence, QColor, QImage
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout,
                             QWidget, QFileDialog, QHBoxLayout, QSizePolicy)
from PyQt5.QtWidgets import QShortcut
from tools.screenshot import ScreenshotOverlay
from tools.clipboard_handler import ClipboardHandler
# Directly import LocalProcessor, but its heavy work will be done on another thread
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
SOFTWARE_VERSION = "v1.0.0"

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
    # 新增信号，用于请求处理器线程处理图片
    process_request = pyqtSignal(QPixmap)

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
        # Reduced margins/spacing in initWidgets instead
        # self.mainLayout.setContentsMargins(20, 20, 20, 20)
        # self.mainLayout.setSpacing(15)


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
        self.process_request.connect(self.local_processor.process_pixmap) # Direct connection works across threads for method calls

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

        icon_path = "images/icon.ico" # Assume this path is correct
        # Check if icon exists, set fallback if not
        if os.path.exists(icon_path):
             self.setWindowIcon(QIcon(icon_path))
        else:
             print(f"Warning: Icon file not found at {icon_path}")
             # Optionally set a default QIcon or leave it as is


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
        self.imageLabel.setScaledContents(False) # We handle scaling manually
        self.imageLabel.setMinimumSize(400, 300) # Adjusted minimum size
        self.imageLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Use centered layout for ImageLabel within imageCard
        imageLayout = QVBoxLayout(self.imageCard)
        imageLayout.setContentsMargins(0, 0, 0, 0)
        imageLayout.addWidget(self.imageLabel, 0, Qt.AlignCenter) # Use alignment flag
        imageLayout.setSpacing(0)


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
        
        self.copyButton = FluentPushButton('复制识别结果(Latex)', self.centralWidget)
        self.copyButton.setIcon(FIF.COPY) # 使用复制图标
        self.copyButton.clicked.connect(self.copy_latex_result)
        self.copyButton.setEnabled(False) # 初始禁用
        
        # 添加按钮到布局
        buttonLayout.addWidget(self.uploadButton)
        buttonLayout.addWidget(self.screenshotButton)
        buttonLayout.addWidget(self.copyButton)
        buttonLayout.addStretch(1) # Push buttons to the left

        # 将所有组件添加到主布局
        self.mainLayout.setContentsMargins(10, 10, 10, 10)
        self.mainLayout.setSpacing(10)
        self.mainLayout.addWidget(statusBarWidget)
        self.mainLayout.addWidget(self.imageCard, 6) # Stretch factor
        self.mainLayout.addWidget(self.latexCard, 4) # Stretch factor
        self.mainLayout.addLayout(buttonLayout)

        self.latexEdit.textChanged.connect(self.update_copy_button_state)
        
    def on_model_loading_finished(self, device_info):
        """模型加载完成后的回调函数"""
        print(f"Received model_loaded signal. Device: {device_info}")
        if "失败" in device_info: # Check if the signal indicates failure
             self.modelStatus.setLoadingFailed(device_info)
             # Keep buttons disabled if loading failed critically? Or enable with warning?
             # Let's keep them disabled if loading failed completely
             self.uploadButton.setEnabled(False)
             self.screenshotButton.setEnabled(False)
             tooltip_text = f"模型加载失败: {device_info}"
             tooltip_state = False # Indicates failure
        else:
             # 更新模型状态指示器
             self.modelStatus.setLoaded(device_info)

             # 启用按钮
             self.uploadButton.setEnabled(True)
             self.screenshotButton.setEnabled(True)
             self.copyButton.setEnabled(True)

             tooltip_text = f"模型加载完成: {device_info}"
             tooltip_state = True # Indicates success

             # Optional: Clear placeholder text if model loaded successfully
             # self.imageLabel.setText("请上传图片或截图")
             # self.latexEdit.setPlaceholderText('识别出的 LaTeX 公式将显示在这里')

        self.update_copy_button_state()
        # 显示提示
        tooltip = StateToolTip("模型状态", tooltip_text, self)
        tooltip.setState(tooltip_state) # Set state icon (check/cross)
        tooltip.show()
        # Position tooltip in the top-right corner
        tooltip.move(self.width() - tooltip.width() - 20, 20)


    def uploadImage(self):
        """
        上传图片功能。
        打开文件对话框让用户选择图片，并在界面上显示。
        """
        fileName, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            ".", # Start directory
            "Image Files (*.png *.jpg *.bmp *.jpeg);;All Files (*)" # Added All Files filter
        )
        if fileName:
            pixmap = QPixmap(fileName)
            if not pixmap.isNull():
                print(f"上传图片: {fileName}, 大小: {pixmap.size()}")
                # Use a timer to ensure the layout has settled before displaying the image
                # Also schedule the processing AFTER display
                QTimer.singleShot(100, lambda: self.display_result_pixmap(pixmap))
            else:
                print(f"无法加载图片: {fileName}")
                # Display empty pixmap and update status
                self.display_result_pixmap(QPixmap())
                self.latexEdit.setText('错误：无法加载图片')
                self.imageLabel.setText("错误：无法加载图片") # Update image label placeholder


    def start_screenshot_process(self):
        """
        开始截图流程 - 确保主窗口完全隐藏后再显示截图覆盖层
        """
        print("开始截图流程...")
        self.hide()
        # Ensure window is hidden before showing overlay
        QTimer.singleShot(100, self.create_and_show_overlay)
        # We don't need to force repaint/processEvents here as much
        # QApplication.processEvents()


    def create_and_show_overlay(self):
        """
        创建并显示截图覆盖层，确保覆盖层获得焦点
        """
        print("创建截图覆盖层...")
        # Ensure previous overlay is deleted
        if self.overlay is not None:
            self.overlay.deleteLater()
            self.overlay = None

        self.overlay = ScreenshotOverlay()
        # Connect signal before showing to avoid race condition
        self.overlay.screenshot_taken.connect(self.handle_screenshot_result)
        self.overlay.screenshot_cancelled.connect(self.handle_screenshot_cancelled)


        if self.overlay.full_screenshot is None:
            print("截图捕获失败或取消")
            self.show_and_activate_main_window() # Return to main window
            self.imageLabel.setText("截图失败或取消")
            self.latexEdit.setText("截图失败或取消")
            self.overlay = None # Clear reference
            return

        print("显示截图覆盖层...")
        self.overlay.show()
        self.overlay.activateWindow()  # Ensure overlay gets focus
        self.overlay.raise_()  # Ensure overlay is on top

    def handle_screenshot_cancelled(self):
         """Handle screenshot cancellation."""
         print("Screenshot cancelled.")
         self.show_and_activate_main_window()
         self.imageLabel.setText("截图已取消")
         self.latexEdit.setText("截图已取消")
         if self.overlay:
              self.overlay.deleteLater()
              self.overlay = None

    def handle_screenshot_result(self, pixmap):
        """
        处理从 ScreenshotOverlay 返回的截图结果。
        """
        print(f"接收到截图结果. Pixmap valid: {not pixmap.isNull()}, Size: {pixmap.size()}")
        # Schedule display_result_pixmap and showing main window
        # Use different timers to ensure order: hide overlay -> show main window -> display/process
        QTimer.singleShot(100, self.show_and_activate_main_window)
        QTimer.singleShot(150, lambda: self.display_result_pixmap(pixmap))


        # Cleanup overlay later if needed, or rely on deleteLater in handle_screenshot_cancelled/result
        if self.overlay:
             # Let handle_screenshot_cancelled/result cleanup the overlay instance
             pass


    def show_and_activate_main_window(self):
        """Helper to show and activate main window after a delay."""
        print("显示并激活主窗口...")
        # Check if overlay still exists and hide/close it if it was not cancelled/handled yet
        if self.overlay and self.overlay.isVisible():
             self.overlay.hide() # or self.overlay.close()

        self.showNormal() # Use showNormal to restore from minimized if needed
        self.activateWindow()
        self.raise_() # Bring to front


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
            # Trigger processing on the worker thread via signal
            # Ensure model is loaded before attempting to process
            if self.local_processor.model is not None: # Check if model is loaded
                 self.latexEdit.setText("正在识别图像...") # Update UI status immediately
                 self.process_request.emit(pixmap) # Emit signal to worker thread
            else:
                 self.latexEdit.setText("模型尚未加载，请稍候...")
                 print("Cannot process image: Model is not loaded yet.")


        else:
            print("显示图片：接收到无效或空图片。")
            self.latexEdit.setText("图片加载失败或取消")
            self.imageLabel.setText("图片加载失败或取消")

            self.original_pixmap = None
            self.imageLabel.setPixmap(QPixmap())
            # Reset placeholder text if no image is shown
            self.imageLabel.setText("请上传图片或截图")
            self.latexEdit.setPlaceholderText('识别出的 LaTeX 公式将显示在这里')


    def _scale_and_display_image(self):
        """
        根据 QLabel (ImageLabel) 的大小缩放并显示 self.original_pixmap。
        修改：确保图片在Label中完全居中显示
        """
        # print("_scale_and_display_image called.")
        if not self.original_pixmap or self.original_pixmap.isNull():
            # print("_scale_and_display_image: 无有效原始图片可显示，清空 QLabel。")
            self.imageLabel.setPixmap(QPixmap())
            # self.imageLabel.setText("无图片") # Keep the main placeholder text
            return

        # Get the size available for the image within the label
        # Use contentsRect() which accounts for padding/margins if any
        lbl_rect = self.imageLabel.contentsRect()
        max_width = lbl_rect.width()
        max_height = lbl_rect.height()

        # Avoid division by zero if label has no size yet
        if max_width <= 0 or max_height <= 0:
             print(f"_scale_and_display_image: Label size invalid: {max_width}x{max_height}")
             return

        # Calculate the scaled size while maintaining aspect ratio
        original_size = self.original_pixmap.size()
        # Use Qt's scaling method directly for simplicity and correctness
        scaled_pixmap = self.original_pixmap.scaled(
             max_width,
             max_height,
             Qt.KeepAspectRatio, # Maintain aspect ratio
             Qt.SmoothTransformation # For better quality scaling
        )

        # Create a canvas (a blank pixmap) the size of the label's contents area
        canvas = QPixmap(lbl_rect.size())
        canvas.fill(Qt.transparent) # Fill with transparency

        # Draw the scaled pixmap onto the canvas, centered
        painter = QPainter(canvas)
        # Calculate the top-left corner position for the scaled image to be centered
        x = (canvas.width() - scaled_pixmap.width()) // 2
        y = (canvas.height() - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()

        # Set the canvas pixmap to the image label
        self.imageLabel.setPixmap(canvas)
        self.imageLabel.setText("") # Clear any placeholder text


    def resizeEvent(self, event):
        """
        窗口大小改变事件，重新缩放图片以适应新的 QLabel 大小。
        """
        super().resizeEvent(event)
        # Use singleShot(0) to allow layout to update before recalculating size
        if self.original_pixmap and not self.original_pixmap.isNull():
             QTimer.singleShot(0, self._scale_and_display_image)


    def load_config(self):
        """加载配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print("Config loaded successfully.")
                return config
        except FileNotFoundError:
            print(f"Config file not found at {config_path}. Using default shortcuts.")
            # If config file doesn't exist, use default configuration
            return {
                "shortcuts": {
                    "screenshot": "Ctrl+Alt+Q",
                    "upload": "Ctrl+U",
                    "paste": "Ctrl+V"
                }
            }
        except json.JSONDecodeError:
            print(f"Error decoding config file at {config_path}. Using default shortcuts.")
             # If config file is invalid JSON, use default configuration
            return {
                "shortcuts": {
                    "screenshot": "Ctrl+Alt+Q",
                    "upload": "Ctrl+U",
                    "paste": "Ctrl+V"
                }
            }
        except Exception as e:
             print(f"An unexpected error occurred loading config: {e}. Using default shortcuts.")
             return {
                "shortcuts": {
                    "screenshot": "Ctrl+Alt+Q",
                    "upload": "Ctrl+U",
                    "paste": "Ctrl+V"
                }
            }


    def setup_shortcuts(self):
        """设置快捷键"""
        # 从配置读取所有快捷键
        shortcuts = self.config.get("shortcuts", {})
        print(f"Setting up shortcuts from config: {shortcuts}")

        # 截图快捷键
        screenshot_seq = shortcuts.get("screenshot", "Ctrl+Alt+Q")
        print(f"Screenshot shortcut: {screenshot_seq}")
        self.shortcut_screenshot = QShortcut(QKeySequence(screenshot_seq), self)
        # Ensure the shortcut is enabled/disabled based on model loaded state
        self.shortcut_screenshot.setEnabled(True) # Disabled initially
        self.shortcut_screenshot.activated.connect(self.start_screenshot_process)

        # 上传图片快捷键
        upload_seq = shortcuts.get("upload", "Ctrl+U")
        print(f"Upload shortcut: {upload_seq}")
        self.shortcut_upload = QShortcut(QKeySequence(upload_seq), self)
        self.shortcut_upload.setEnabled(True) # Disabled initially
        self.shortcut_upload.activated.connect(self.uploadImage)

        # 初始化剪切板处理器
        self.clipboard_handler = ClipboardHandler(self)
        self.clipboard_handler.image_received.connect(self.handle_clipboard_image)

        # 粘贴快捷键
        paste_seq = shortcuts.get("paste", "Ctrl+V")
        print(f"Paste shortcut: {paste_seq}")
        self.shortcut_paste = QShortcut(QKeySequence(paste_seq), self)
        self.shortcut_paste.setEnabled(True) # Disabled initially
        self.shortcut_paste.activated.connect(self.clipboard_handler.handle_paste)


    def handle_clipboard_image(self, image: QImage):
        """处理从剪切板粘贴的图片 (QImage)"""
        print(f"Received image from clipboard. Format: {image.format()}")
        pixmap = QPixmap.fromImage(image)
        if not pixmap.isNull():
            self.display_result_pixmap(pixmap)
        else:
            print("Clipboard image is null.")
            self.latexEdit.setText("剪切板中的图片无效")
            self.imageLabel.setText("剪切板中的图片无效")


    # Remove this method as processing is now triggered via signal from display_result_pixmap
    # def process_image(self, pixmap: QPixmap):
    #     """异步处理图像 - This method is no longer used directly"""
    #     pass

    def on_recognition_finished(self, result):
        """识别完成回调"""
        print(f"接收到识别结果:\n{result[:100]}...") # Print only first 100 chars
        self.latexEdit.setText(result)


    def closeEvent(self, event):
        """窗口关闭时清理线程"""
        print("Closing main window, quitting processor thread...")
        # Request the thread to stop its event loop
        self.processor_thread.quit()
        # Wait until the thread finishes execution (e.g., after current task completes)
        self.processor_thread.wait(5000) # Wait up to 5 seconds
        if self.processor_thread.isRunning():
             print("Warning: Processor thread did not terminate gracefully.")
             # Optionally terminate forcefully if waiting is not enough
             # self.processor_thread.terminate()
             # self.processor_thread.wait()
        else:
             print("Processor thread finished.")

        # Clean up overlay if it exists and is visible (e.g., user closes during screenshot)
        if self.overlay is not None and self.overlay.isVisible():
            self.overlay.close()
            self.overlay = None # Clear reference

        super().closeEvent(event)
    
    def copy_latex_result(self):
        """将识别出的LaTeX结果复制到剪贴板"""
        latex_text = self.latexEdit.toPlainText()
        if latex_text: # Only copy if there is text
            clipboard = QApplication.clipboard()
            clipboard.setText(latex_text)
            print("LaTeX result copied to clipboard.")
            # ====== 可选: 显示复制成功提示 ======
            tooltip = StateToolTip("复制成功", "LaTeX 代码已复制到剪贴板", self)
            tooltip.setState(True) # True shows success icon
            # Position tooltip near the button or result box
            # A simple position, adjust as needed
            tooltip.move(self.copyButton.mapToGlobal(QPoint(self.copyButton.width() // 2 - tooltip.width() // 2, -tooltip.height() - 10)))
            tooltip.show()
        else:
            print("No LaTeX result to copy.")
            # ====== 可选: 显示无结果提示 ======
            tooltip = StateToolTip("无结果", "没有可复制的LaTeX代码", self)
            tooltip.setState(False) # False shows failure icon
            tooltip.move(self.copyButton.mapToGlobal(QPoint(self.copyButton.width() // 2 - tooltip.width() // 2, -tooltip.height() - 10)))
            tooltip.show()

    def update_copy_button_state(self):
        """根据latexEdit的内容启用/禁用复制按钮"""
        # 获取当前文本，忽略前后空白
        text = self.latexEdit.toPlainText().strip()
        # 如果文本非空，且不等于占位符文本，则启用按钮
        # 检查占位符是为了避免在没有识别结果时复制占位符文字
        is_placeholder = (text == self.latexEdit.placeholderText().strip())
        self.copyButton.setEnabled(bool(text) and not is_placeholder)

if __name__ == '__main__':
    # 启用高 DPI 支持 (如果开启，可能会影响多屏截图时的准确性)
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    # QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough) # Optional policy

    app = QApplication(sys.argv)

    # Set theme (optional, but good practice if using Fluent UI)
    # setTheme(Theme.DARK) # or Theme.LIGHT

    main_window = MainWindow()
    main_window.show()

    # Start the Qt event loop
    sys.exit(app.exec_())