# tools/screenshot.py

import sys
from PyQt5.QtWidgets import QWidget, QApplication, QDesktopWidget # QDesktopWidget might be deprecated in newer Qt versions, using QApplication.screens() is preferred
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QCursor
from PyQt5.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal, QTimer # Import QTimer if using the init failure check

class ScreenshotOverlay(QWidget):
    """
    截图覆盖层，用于选择截图区域
    功能：
    1. 捕获整个桌面截图作为背景
    2. 允许用户通过鼠标拖拽选择区域
    3. 提供十字辅助线帮助精确定位
    4. 支持ESC键取消截图
    """
    screenshot_taken = pyqtSignal(QPixmap)  # 截图完成信号
    # 添加截图取消信号
    screenshot_cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()
        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)

        # 初始化变量
        self.start_pos = QPoint()
        self.end_pos = QPoint()
        self.is_selecting = False
        self.full_screenshot = None
        self.overlay_color = QColor(0, 0, 0, 120)  # 半透明遮罩颜色

        # 获取桌面几何区域
        self.desktop_rect = self.get_desktop_geometry()

        # 捕获全屏截图
        self.capture_full_desktop()

        # !!! 重要检查 !!! 如果截图失败，立即关闭窗口并通知主窗口
        # 注意：这里的close会在init完成后立即发生，主窗口需要处理这种情况
        if self.full_screenshot is None or self.full_screenshot.isNull():
             print("致命错误: 捕获屏幕截图失败。")
             # We cannot emit a signal here immediately in __init__
             # The main window should check if self.overlay.full_screenshot is None after creating it.
             # Or, we can schedule a close and the main window will handle the overlay being closed unexpectedly.
             QTimer.singleShot(10, self.close) # Schedule close shortly
             # We don't emit cancelled here because main window doesn't expect signal until shown/interaction
             return # Exit init early if capture failed


        # 设置窗口大小为整个虚拟桌面
        # Only set geometry and show if capture was successful
        self.setGeometry(self.desktop_rect)
        self.setMouseTracking(True)

        # Optionally show the overlay immediately here if that fits the main window logic better
        # self.show() # Main window is responsible for showing after hiding itself


    def get_desktop_geometry(self):
        """获取包含所有屏幕的总几何区域"""
        desktop_rect = QRect()
        # Use QApplication.screens() for multi-monitor support
        for screen in QApplication.screens():
            desktop_rect = desktop_rect.united(screen.geometry())
        return desktop_rect

    def capture_full_desktop(self):
        """捕获整个虚拟桌面截图"""
        screen = QApplication.primaryScreen()
        if screen is None:
             print("错误: 无法获取主屏幕。")
             self.full_screenshot = None
             return

        try:
            # Ensure QApplication is instantiated before grabbing
            if QApplication.instance() is None:
                print("Warning: QApplication not instantiated. Creating one temporarily.")
                QApplication([]) # Create a QApplication if none exists (shouldn't happen in main app)

            # Grab the full virtual desktop
            # Using screen.grabWindow(0) with desktop rect coordinates
            self.full_screenshot = screen.grabWindow(
                0,
                self.desktop_rect.x(),
                self.desktop_rect.y(),
                self.desktop_rect.width(),
                self.desktop_rect.height()
            )
            if self.full_screenshot.isNull():
                 print("捕获屏幕截图失败: grabWindow返回空pixmap。")
            else:
                 print(f"成功捕获屏幕截图，大小: {self.full_screenshot.size()}")

        except Exception as e:
            print(f"捕获屏幕截图过程中发生异常: {e}")
            self.full_screenshot = None


    def paintEvent(self, event):
        """绘制事件：绘制背景、遮罩、选区和辅助线"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制半透明遮罩层
        # Only draw if screenshot was successful
        if self.full_screenshot and not self.full_screenshot.isNull():
             painter.drawPixmap(0, 0, self.full_screenshot) # Draw full background first
             painter.fillRect(self.rect(), self.overlay_color) # Then draw overlay on top
        else:
             # If screenshot failed, just draw a grey background or similar
             painter.fillRect(self.rect(), QColor(100, 100, 100)) # Grey background if capture failed
             painter.setPen(Qt.white)
             painter.drawText(self.rect(), Qt.AlignCenter, "无法捕获屏幕截图")


        # 如果正在选择，绘制清晰的选区和边框
        if self.is_selecting and not self.start_pos.isNull() and not self.end_pos.isNull():
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()

            # Ensure screenshot is valid before drawing the selected area
            if self.full_screenshot and not self.full_screenshot.isNull():
                 # 在遮罩层上显示选区部分的原始截图
                 # Use QPainter.CompositionMode_Source to draw the original pixmap over the mask in the rect
                 painter.setCompositionMode(QPainter.CompositionMode_SourceOver) # Or Source if you want to replace the mask
                 painter.drawPixmap(selection_rect, self.full_screenshot, selection_rect)
                 painter.setCompositionMode(QPainter.CompositionMode_SourceOver) # Reset composition mode

            # 绘制选区边框
            pen = QPen(Qt.red, 1, Qt.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(selection_rect)


        # 绘制鼠标位置的十字辅助线
        # Only draw if screenshot was successful and not null, otherwise coordinates might be meaningless
        if self.full_screenshot and not self.full_screenshot.isNull() and not self.end_pos.isNull():
            pen_guide = QPen(Qt.red, 1, Qt.DotLine)
            painter.setPen(pen_guide)
            # 水平线
            painter.drawLine(0, self.end_pos.y(), self.width(), self.end_pos.y())
            # 垂直线
            painter.drawLine(self.end_pos.x(), 0, self.end_pos.x(), self.height())


    def mousePressEvent(self, event):
        """鼠标按下事件：开始选择"""
        if event.button() == Qt.LeftButton and self.full_screenshot and not self.full_screenshot.isNull():
            self.start_pos = event.pos()
            self.end_pos = event.pos() # Initialize end_pos as well
            self.is_selecting = True
            self.update() # Trigger repaint to show initial selection and guides

    def mouseMoveEvent(self, event):
        """鼠标移动事件：更新选择区域或辅助线位置"""
        # Only track mouse move for selection if screenshot was successful
        if self.full_screenshot and not self.full_screenshot.isNull():
            self.end_pos = event.pos()
            # Only update if selecting or simply moving the mouse (for guides)
            if self.is_selecting or self.cursor().shape() == Qt.CrossCursor:
                 self.update()


    def mouseReleaseEvent(self, event):
        """鼠标释放事件：完成选择，截取图片或取消"""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()

            # 检查选择区域是否有效
            if selection_rect.width() > 0 and selection_rect.height() > 0:
                # 从全屏截图中复制选定区域
                if self.full_screenshot and not self.full_screenshot.isNull():
                    captured_pixmap = self.full_screenshot.copy(selection_rect)
                    print(f"截图完成。大小: {captured_pixmap.size()}")
                    self.screenshot_taken.emit(captured_pixmap) # 发射截图完成信号
                else:
                     # If selection was made but screenshot was somehow lost, treat as cancelled
                     print("选择区域有效，但原始截图丢失。取消。")
                     self.screenshot_cancelled.emit() # 发射截图取消信号
            else:
                # 选择区域无效，发射取消信号
                print("选择区域无效（宽度或高度为零）。取消。")
                self.screenshot_cancelled.emit()  # 发射截图取消信号

            self.close()  # 关闭覆盖层


    def keyPressEvent(self, event):
        """键盘事件：按ESC取消截图"""
        if event.key() == Qt.Key_Escape:
            print("通过ESC键取消截图。")
            self.screenshot_cancelled.emit()  # 发射截图取消信号
            self.close() # 关闭覆盖层


if __name__ == '__main__':
    # Example usage (for testing ScreenshotOverlay alone)
    app = QApplication(sys.argv)

    # Set High DPI scaling if needed for your system
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    # QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    # QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    overlay = ScreenshotOverlay()

    # Connect signals for testing
    def on_screenshot_taken(pixmap):
        print(f"Screenshot taken! Size: {pixmap.size()}")
        if not pixmap.isNull():
             pixmap.save("screenshot_test.png") # Save for verification
             print("Saved as screenshot_test.png")
        app.quit()

    def on_screenshot_cancelled():
        print("Screenshot cancelled.")
        app.quit()

    overlay.screenshot_taken.connect(on_screenshot_taken)
    overlay.screenshot_cancelled.connect(on_screenshot_cancelled)

    # Check if the overlay was successfully initialized (screenshot captured)
    if overlay.full_screenshot is not None and not overlay.full_screenshot.isNull():
        overlay.show() # Show the overlay for user interaction
        sys.exit(app.exec_())
    else:
        # Handle the case where the overlay couldn't even capture the screen
        print("Overlay could not be shown due to screen capture failure.")
        sys.exit(1) # Exit with an error code