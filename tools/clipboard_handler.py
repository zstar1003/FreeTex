from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QClipboard, QImage
from PyQt5.QtWidgets import QApplication

class ClipboardHandler(QObject):
    """
    剪切板处理器，负责处理从剪切板粘贴内容
    功能：
    1. 监听Ctrl+V快捷键
    2. 获取剪切板中的图片或文本
    3. 发出信号通知主窗口处理
    """
    image_received = pyqtSignal(QImage)  # 当剪切板中有图片时发出
    text_received = pyqtSignal(str)     # 当剪切板中有文本时发出

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clipboard = QApplication.clipboard()

    def handle_paste(self):
        """处理粘贴操作"""
        if self.clipboard.mimeData().hasImage():
            # 处理图片
            image = self.clipboard.image()
            if not image.isNull():
                self.image_received.emit(image)
        elif self.clipboard.mimeData().hasText():
            # 处理文本
            text = self.clipboard.text()
            if text.strip():
                self.text_received.emit(text)