import sys
import logging
from PyQt5.QtWidgets import QWidget, QApplication, QDesktopWidget
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QCursor
from PyQt5.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal, QTimer

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
    screenshot_cancelled = pyqtSignal()    # 截图取消信号

    def __init__(self):
        super().__init__()
        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.logger = logging.getLogger('logs/FreeTex.log')

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

        # 如果截图失败，立即关闭窗口并通知主窗口
        if self.full_screenshot is None or self.full_screenshot.isNull():
             self.logger.error("致命错误: 捕获屏幕截图失败")
             QTimer.singleShot(10, self.close)
             return

        # 设置窗口大小为整个虚拟桌面
        self.setGeometry(self.desktop_rect)
        self.setMouseTracking(True)

    def get_desktop_geometry(self):
        """获取包含所有屏幕的总几何区域"""
        desktop_rect = QRect()
        for screen in QApplication.screens():
            desktop_rect = desktop_rect.united(screen.geometry())
        return desktop_rect

    def capture_full_desktop(self):
        """捕获整个虚拟桌面截图"""
        screen = QApplication.primaryScreen()
        if screen is None:
             self.logger.error("无法获取主屏幕")
             self.full_screenshot = None
             return

        try:
            if QApplication.instance() is None:
                self.logger.warning("QApplication未实例化，临时创建一个")
                QApplication([])

            self.full_screenshot = screen.grabWindow(
                0,
                self.desktop_rect.x(),
                self.desktop_rect.y(),
                self.desktop_rect.width(),
                self.desktop_rect.height()
            )
            if self.full_screenshot.isNull():
                 self.logger.error("捕获屏幕截图失败: grabWindow返回空pixmap")
            else:
                 self.logger.info(f"成功捕获屏幕截图，大小: {self.full_screenshot.size()}")

        except Exception as e:
            self.logger.error(f"捕获屏幕截图过程中发生异常: {e}")
            self.full_screenshot = None


    def paintEvent(self, event):
        """绘制事件：绘制背景、遮罩、选区和辅助线"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制半透明遮罩层
        if self.full_screenshot and not self.full_screenshot.isNull():
             painter.drawPixmap(0, 0, self.full_screenshot)
             painter.fillRect(self.rect(), self.overlay_color) 
        else:
             painter.fillRect(self.rect(), QColor(100, 100, 100))
             painter.setPen(Qt.white)
             painter.drawText(self.rect(), Qt.AlignCenter, "无法捕获屏幕截图")


        # 如果正在选择，绘制清晰的选区和边框
        if self.is_selecting and not self.start_pos.isNull() and not self.end_pos.isNull():
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()

            if self.full_screenshot and not self.full_screenshot.isNull():
                 # 在遮罩层上显示选区部分的原始截图
                 painter.setCompositionMode(QPainter.CompositionMode_SourceOver) 
                 painter.drawPixmap(selection_rect, self.full_screenshot, selection_rect)
                 painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # 绘制选区边框
            pen = QPen(Qt.red, 1, Qt.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(selection_rect)


        # 绘制鼠标位置的十字辅助线
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
            self.end_pos = event.pos()
            self.is_selecting = True
            self.update() 

    def mouseMoveEvent(self, event):
        """鼠标移动事件：更新选择区域或辅助线位置"""
        if self.full_screenshot and not self.full_screenshot.isNull():
            self.end_pos = event.pos()
            if self.is_selecting or self.cursor().shape() == Qt.CrossCursor:
                 self.update()


    def mouseReleaseEvent(self, event):
        """鼠标释放事件：完成选择，截取图片或取消"""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()

            if selection_rect.width() > 0 and selection_rect.height() > 0:
                if self.full_screenshot and not self.full_screenshot.isNull():
                    captured_pixmap = self.full_screenshot.copy(selection_rect)
                    self.logger.info(f"截图完成。大小: {captured_pixmap.size()}")
                    self.screenshot_taken.emit(captured_pixmap)
                else:
                     self.logger.warning("选择区域有效，但原始截图丢失。取消。")
                     self.screenshot_cancelled.emit()
            else:
                self.logger.warning("选择区域无效（宽度或高度为零）。取消。")
                self.screenshot_cancelled.emit()

            self.close()  # 关闭覆盖层


    def keyPressEvent(self, event):
        """键盘事件：按ESC取消截图"""
        if event.key() == Qt.Key_Escape:
            self.logger.info("通过ESC键取消截图")
            self.screenshot_cancelled.emit()
            self.close() # 关闭覆盖层