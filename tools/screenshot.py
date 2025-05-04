import sys
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QCursor
from PyQt5.QtCore import Qt, QRect, QPoint, QSize, pyqtSignal

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
        try:
            self.full_screenshot = screen.grabWindow(
                0,  # 0表示捕获整个桌面
                self.desktop_rect.x(),
                self.desktop_rect.y(),
                self.desktop_rect.width(),
                self.desktop_rect.height()
            )
        except Exception as e:
            print(f"捕获屏幕截图失败: {e}")
            self.full_screenshot = None

    def paintEvent(self, event):
        """绘制事件：绘制背景、遮罩、选区和辅助线"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制半透明遮罩层
        painter.fillRect(self.rect(), self.overlay_color)

        # 如果正在选择，绘制清晰的选区和边框
        if self.is_selecting and not self.start_pos.isNull() and not self.end_pos.isNull():
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()
            
            # 在遮罩层上显示选区部分的原始截图
            painter.drawPixmap(selection_rect, self.full_screenshot, selection_rect)
            
            # 绘制选区边框
            pen = QPen(Qt.red, 1, Qt.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(selection_rect)

        # 绘制鼠标位置的十字辅助线
        if not self.end_pos.isNull():
            pen_guide = QPen(Qt.red, 1, Qt.DotLine)
            painter.setPen(pen_guide)
            # 水平线
            painter.drawLine(0, self.end_pos.y(), self.width(), self.end_pos.y())
            # 垂直线
            painter.drawLine(self.end_pos.x(), 0, self.end_pos.x(), self.height())

    def mousePressEvent(self, event):
        """鼠标按下事件：开始选择"""
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        """鼠标移动事件：更新选择区域或辅助线位置"""
        self.end_pos = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件：完成选择，截取图片"""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()

            if selection_rect.width() > 0 and selection_rect.height() > 0:
                # 从全屏截图中复制选定区域
                if self.full_screenshot and not self.full_screenshot.isNull():
                    captured_pixmap = self.full_screenshot.copy(selection_rect)
                    self.screenshot_taken.emit(captured_pixmap)
                else:
                    self.screenshot_taken.emit(QPixmap())  # 发射空Pixmap表示失败
            else:
                self.screenshot_taken.emit(QPixmap())  # 发射空Pixmap

            self.close()  # 关闭覆盖层

    def keyPressEvent(self, event):
        """键盘事件：按ESC取消截图"""
        if event.key() == Qt.Key_Escape:
            self.screenshot_taken.emit(QPixmap())  # 发射空Pixmap表示取消
            self.close()