from tools.config_store import read_config, update_config_section
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QWidget, QFormLayout, QDialogButtonBox
)
from PyQt5.QtGui import QKeySequence
from qfluentwidgets import (
    LineEdit,
    InfoBar,
    InfoBarPosition,
)


class ShortcutLineEdit(LineEdit):
    """自定义快捷键输入框，支持按键捕获"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("点击此处按下快捷键组合")
        self.setReadOnly(True)  # 设置为只读，防止直接输入

    def keyPressEvent(self, event):
        """捕获按键事件并转换为快捷键字符串"""
        # 忽略单独的修饰键
        if event.key() in [Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta]:
            return

        # 获取修饰键
        modifiers = event.modifiers()
        key = event.key()

        # 构建快捷键序列
        key_sequence = QKeySequence(modifiers | key)
        shortcut_text = key_sequence.toString()

        # 设置文本
        if shortcut_text:
            self.setText(shortcut_text)

    def mousePressEvent(self, event):
        """点击时清空内容，准备输入新的快捷键"""
        self.clear()
        super().mousePressEvent(event)


class ShortcutConfigDialog(QDialog):
    """快捷键设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("快捷键设置")
        # 移除问号按钮
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint | Qt.WindowCloseButtonHint)
        self.setModal(True)
        self.resize(450, 250)

        # 加载现有配置
        self.load_config()

        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # 添加说明文字
        info_label = QLabel("点击输入框后按下快捷键组合来设置")
        info_label.setStyleSheet("color: #606060; font-size: 12px;")
        layout.addWidget(info_label)

        # 创建表单布局
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form_layout.setContentsMargins(0, 0, 0, 0)

        # 截图快捷键
        screenshot_label = QLabel("截图快捷键:")
        screenshot_label.setContentsMargins(20, 0, 0, 0)
        self.screenshotEdit = ShortcutLineEdit()
        self.screenshotEdit.setText(self.config.get("shortcuts", {}).get("screenshot", "Ctrl+Alt+Q"))
        form_layout.addRow(screenshot_label, self.screenshotEdit)

        # 上传图片快捷键
        upload_label = QLabel("上传图片快捷键:")
        upload_label.setContentsMargins(20, 0, 0, 0)
        self.uploadEdit = ShortcutLineEdit()
        self.uploadEdit.setText(self.config.get("shortcuts", {}).get("upload", "Ctrl+U"))
        form_layout.addRow(upload_label, self.uploadEdit)

        # 粘贴图片快捷键
        paste_label = QLabel("粘贴图片快捷键:")
        paste_label.setContentsMargins(20, 0, 0, 0)
        self.pasteEdit = ShortcutLineEdit()
        self.pasteEdit.setText(self.config.get("shortcuts", {}).get("paste", "Ctrl+V"))
        form_layout.addRow(paste_label, self.pasteEdit)

        layout.addWidget(form_widget)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        # 设置中文按钮文本
        button_box.button(QDialogButtonBox.Ok).setText("确认")
        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        button_box.accepted.connect(self.save_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_config(self):
        """加载配置文件"""
        try:
            self.config = read_config()
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.config = {"shortcuts": {}}

    def save_and_accept(self):
        """保存配置并关闭对话框"""
        # 验证快捷键不为空
        screenshot = self.screenshotEdit.text().strip()
        upload = self.uploadEdit.text().strip()
        paste = self.pasteEdit.text().strip()

        if not screenshot or not upload or not paste:
            InfoBar.error(
                title="错误",
                content="所有快捷键都必须设置",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        # 检查快捷键是否重复
        shortcuts = [screenshot, upload, paste]
        if len(shortcuts) != len(set(shortcuts)):
            InfoBar.warning(
                title="警告",
                content="快捷键不能重复",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return

        # 更新配置
        if "shortcuts" not in self.config:
            self.config["shortcuts"] = {}

        self.config["shortcuts"]["screenshot"] = screenshot
        self.config["shortcuts"]["upload"] = upload
        self.config["shortcuts"]["paste"] = paste

        # 保存到文件
        try:
            update_config_section("shortcuts", self.config["shortcuts"])

            InfoBar.success(
                title="成功",
                content="快捷键设置已保存，重启应用后生效",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            # 延迟关闭对话框，让用户看到成功提示
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1000, self.accept)

        except Exception as e:
            InfoBar.error(
                title="保存失败",
                content=f"无法保存配置: {str(e)}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
