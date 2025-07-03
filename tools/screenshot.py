import logging
import platform
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, QPoint, pyqtSignal, QTimer


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
    screenshot_cancelled = pyqtSignal()  # 截图取消信号

    def __init__(self):
        super().__init__()
        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.logger = logging.getLogger("logs/FreeTex.log")

        # 检测操作系统和高DPI支持
        self.is_macos = platform.system() == "Darwin"
        self.device_pixel_ratio = 1.0

        # 初始化变量
        self.start_pos = QPoint()
        self.end_pos = QPoint()
        self.is_selecting = False
        self.has_moved = False
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
        """获取包含所有屏幕的总几何区域，并记录设备像素比"""
        desktop_rect = QRect()

        # 获取主屏幕信息
        primary_screen = QApplication.primaryScreen()
        if primary_screen:
            self.device_pixel_ratio = primary_screen.devicePixelRatio()
            self.logger.info(f"检测到设备像素比: {self.device_pixel_ratio}")

        # 计算所有屏幕的联合区域
        for screen in QApplication.screens():
            desktop_rect = desktop_rect.united(screen.geometry())

        self.logger.info(f"桌面几何区域: {desktop_rect}")
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

            if self.is_macos:
                self.full_screenshot = screen.grabWindow(0)
            else:
                self.full_screenshot = screen.grabWindow(
                    0,
                    self.desktop_rect.x(),
                    self.desktop_rect.y(),
                    self.desktop_rect.width(),
                    self.desktop_rect.height(),
                )
            if self.full_screenshot.isNull():
                self.logger.error("捕获屏幕截图失败: grabWindow返回空pixmap")
            else:
                self.logger.info(
                    f"成功捕获屏幕截图，大小: {self.full_screenshot.size()}"
                )

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
        if (
            self.is_selecting
            and self.has_moved
            and not self.start_pos.isNull()
            and not self.end_pos.isNull()
        ):
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()

            if self.full_screenshot and not self.full_screenshot.isNull():
                # 在遮罩层上显示选区部分的原始截图
                if self.is_macos:
                    # 计算在截图中的对应区域
                    screenshot_rect = self.calculate_screenshot_rect(selection_rect)

                    # 从原始截图中提取选择的区域并显示
                    cropped_pixmap = self.full_screenshot.copy(screenshot_rect)
                    painter.drawPixmap(selection_rect, cropped_pixmap)
                else:
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                    painter.drawPixmap(
                        selection_rect, self.full_screenshot, selection_rect
                    )
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # 绘制选区边框
            pen = QPen(Qt.red, 1, Qt.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(selection_rect)

        # 绘制鼠标位置的十字辅助线
        if (
            self.full_screenshot
            and not self.full_screenshot.isNull()
            and not self.end_pos.isNull()
            and not self.is_selecting
        ):
            pen_guide = QPen(Qt.red, 1, Qt.DotLine)
            painter.setPen(pen_guide)
            # 水平线
            painter.drawLine(0, self.end_pos.y(), self.width(), self.end_pos.y())
            # 垂直线
            painter.drawLine(self.end_pos.x(), 0, self.end_pos.x(), self.height())

    def calculate_screenshot_rect(self, selection_rect):
        # 获取截图的实际尺寸和桌面的逻辑尺寸
        screenshot_size = self.full_screenshot.size()
        desktop_size = self.desktop_rect.size()

        # 计算缩放比例
        scale_x = screenshot_size.width() / desktop_size.width()
        scale_y = screenshot_size.height() / desktop_size.height()

        # 计算在截图中的对应区域
        screenshot_rect = QRect(
            int(selection_rect.x() * scale_x),
            int(selection_rect.y() * scale_y),
            int(selection_rect.width() * scale_x),
            int(selection_rect.height() * scale_y),
        )

        return screenshot_rect

    def mousePressEvent(self, event):
        """鼠标按下事件：开始选择"""
        if (
            event.button() == Qt.LeftButton
            and self.full_screenshot
            and not self.full_screenshot.isNull()
        ):
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.is_selecting = True
            self.has_moved = False
            self.update()

    def mouseMoveEvent(self, event):
        """鼠标移动事件：更新选择区域或辅助线位置"""
        if self.full_screenshot and not self.full_screenshot.isNull():
            current_pos = event.pos()

            if self.is_selecting:
                # 检查是否移动了足够的距离
                if not self.has_moved:
                    move_distance = (
                        (current_pos.x() - self.start_pos.x()) ** 2
                        + (current_pos.y() - self.start_pos.y()) ** 2
                    ) ** 0.5
                    if move_distance > 5:
                        self.has_moved = True

                self.end_pos = current_pos
                if self.has_moved:
                    self.update()
            else:
                self.end_pos = current_pos
                self.update()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件：完成选择，截取图片或取消"""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False

            if self.is_macos:
                if self.has_moved:
                    selection_rect = QRect(self.start_pos, self.end_pos).normalized()

                    if selection_rect.width() > 5 and selection_rect.height() > 5:
                        if self.full_screenshot and not self.full_screenshot.isNull():
                            # 计算在原始截图中的精确区域
                            screenshot_rect = self.calculate_screenshot_rect(
                                selection_rect
                            )

                            # 从原始高分辨率截图中提取区域
                            captured_pixmap = self.full_screenshot.copy(screenshot_rect)

                            # 验证截图质量
                            if not captured_pixmap.isNull():
                                self.logger.info(f"截图完成")
                                self.logger.info(f"选择区域: {selection_rect}")
                                self.logger.info(f"截图区域: {screenshot_rect}")
                                self.logger.info(f"输出尺寸: {captured_pixmap.size()}")

                                # 发射高质量的原始截图
                                self.screenshot_taken.emit(captured_pixmap)
                            else:
                                self.logger.error("截图区域无效")
                                self.screenshot_cancelled.emit()
                        else:
                            self.logger.warning("原始截图丢失")
                            self.screenshot_cancelled.emit()
                    else:
                        self.logger.warning("选择区域过小")
                        self.screenshot_cancelled.emit()
                else:
                    self.logger.warning("未检测到有效拖拽")
                    self.screenshot_cancelled.emit()

                self.close()
            else:
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
            self.close()  # 关闭覆盖层
