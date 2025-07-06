from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QWidget, QFormLayout, QDialogButtonBox, QRadioButton
)
from PyQt5.QtGui import QFontDatabase
from qfluentwidgets import (
    ComboBox,
    LineEdit,
    PushButton,
    InfoBar,
    InfoBarPosition,
)
import os
import sys

def resource_path(relative_path):
    """获取资源的绝对路径"""
    if getattr(sys, 'frozen', False):
        # 运行在 PyInstaller bundle 中
        base_path = sys._MEIPASS
    else:
        # 运行在普通 Python 环境中
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class ModelConfigDialog(QDialog):
    """模型配置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("多模态识别设置")
        # 移除问号按钮
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint | Qt.WindowCloseButtonHint)
        self.setModal(True)

        # 加载字体
        try:
            font_path = resource_path(os.path.join("resources", "fonts", "Noto_Serif_SC", "NotoSerifSC-VariableFont_wght_3500_punc.ttf"))
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id < 0:
                print(f"Warning: Failed to load font: {font_path}")
            else:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    print(f"Successfully loaded font family: {font_families[0]}")
        except Exception as e:
            print(f"Error loading font: {str(e)}")
        
        # 创建主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # 创建表单布局
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form_layout.setContentsMargins(0, 0, 0, 0)
        
        # 启用状态（使用单选按钮）
        enable_widget = QWidget()
        enable_layout = QHBoxLayout(enable_widget)
        enable_layout.setContentsMargins(0, 0, 0, 0)
        enable_layout.setSpacing(20)
        
        self.enableRadioYes = QRadioButton("是")
        self.enableRadioNo = QRadioButton("否")
        enable_layout.addWidget(self.enableRadioYes)
        enable_layout.addWidget(self.enableRadioNo)
        enable_layout.addStretch()
        
        # 创建带有额外左边距的标签
        enable_label = QLabel("启用多模态识别:")
        enable_label.setContentsMargins(20, 0, 0, 0)
        form_layout.addRow(enable_label, enable_widget)
        
        # 模型提供商
        provider_label = QLabel("模型提供商:")
        provider_label.setContentsMargins(20, 0, 0, 0)
        self.providerComboBox = ComboBox()
        self.providerComboBox.addItems(["硅基流动", "自定义"])
        self.providerComboBox.currentTextChanged.connect(self.on_provider_changed)
        form_layout.addRow(provider_label, self.providerComboBox)

        # API地址
        api_url_label = QLabel("API地址:")
        api_url_label.setContentsMargins(20, 0, 0, 0)
        self.apiUrlEdit = LineEdit()
        self.apiUrlEdit.setPlaceholderText("例如: https://api.example.com/v1")
        form_layout.addRow(api_url_label, self.apiUrlEdit)

        # API Key
        api_key_label = QLabel("API Key:")
        api_key_label.setContentsMargins(20, 0, 0, 0)
        self.apiKeyEdit = LineEdit()
        self.apiKeyEdit.setPlaceholderText("请输入API Key")
        form_layout.addRow(api_key_label, self.apiKeyEdit)

        # 模型名称
        model_label = QLabel("模型名称:")
        model_label.setContentsMargins(20, 0, 0, 0)
        self.modelEdit = LineEdit()
        self.modelEdit.setPlaceholderText("例如: Qwen/Qwen2.5-VL-72B-Instruct")
        form_layout.addRow(model_label, self.modelEdit)

        # 添加表单到主布局
        layout.addWidget(form_widget)

        # 添加测试连接按钮（居中）
        test_button_layout = QHBoxLayout()
        self.testButton = PushButton("测试连接")
        self.testButton.setFixedWidth(120)
        self.testButton.clicked.connect(self.test_connection)
        test_button_layout.addStretch()
        test_button_layout.addWidget(self.testButton)
        test_button_layout.addStretch()
        layout.addLayout(test_button_layout)

        # 添加按钮盒子
        button_box = QDialogButtonBox()
        # 使用FluentPushButton替代默认按钮
        self.okButton = PushButton("确定")
        self.cancelButton = PushButton("取消")
        button_box.addButton(self.okButton, QDialogButtonBox.AcceptRole)
        button_box.addButton(self.cancelButton, QDialogButtonBox.RejectRole)
        
        # 连接信号
        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)
        
        layout.addWidget(button_box)

        # 设置固定大小
        self.setFixedSize(500, 400)
        
        # 加载配置
        self.load_config()

        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                font-size: 14px;
            }
            LineEdit {
                min-width: 300px;
                padding: 5px;
            }
            ComboBox {
                min-width: 300px;
            }
            QRadioButton {
                font-size: 14px;
                spacing: 5px;
            }
        """)

    def showEvent(self, event):
        """显示事件，用于居中显示对话框"""
        super().showEvent(event)
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)

    def on_provider_changed(self, provider):
        """处理提供商变更"""
        if provider == "硅基流动":
            self.apiUrlEdit.setText("https://api.siliconflow.cn/v1")
            self.apiUrlEdit.setReadOnly(True)
            self.modelEdit.setText("Qwen/Qwen2.5-VL-72B-Instruct")
        else:
            self.apiUrlEdit.clear()
            self.apiUrlEdit.setReadOnly(False)
            self.modelEdit.clear()

    def load_config(self):
        """从配置文件加载设置"""
        try:
            import json
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                model_config = config.get("model_config", {})
                
                # 设置控件值
                is_enabled = model_config.get("enabled", False)
                self.enableRadioYes.setChecked(is_enabled)
                self.enableRadioNo.setChecked(not is_enabled)
                
                self.providerComboBox.setCurrentText(model_config.get("provider", "硅基流动"))
                self.apiUrlEdit.setText(model_config.get("api_url", "https://api.siliconflow.cn/v1"))
                self.apiKeyEdit.setText(model_config.get("api_key", ""))
                self.modelEdit.setText(model_config.get("model_name", "Qwen/Qwen2.5-VL-72B-Instruct"))
                
                # 根据提供商设置URL编辑状态
                self.on_provider_changed(self.providerComboBox.currentText())
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"加载配置失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def save_config(self):
        """保存设置到配置文件"""
        try:
            import json
            # 读取现有配置
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
            except:
                config = {}

            # 更新模型配置
            config["model_config"] = {
                "enabled": self.enableRadioYes.isChecked(),
                "provider": self.providerComboBox.currentText(),
                "api_url": self.apiUrlEdit.text(),
                "api_key": self.apiKeyEdit.text(),
                "model_name": self.modelEdit.text(),
                "system_prompt": "你是一个专业的数学公式识别系统，请严格按照以下要求操作：\n1. 专注识别图像中的数学公式、符号、希腊字母、运算符等\n2. 输出标准LaTeX代码，确保可被编译器解析\n3. 所有公式必须转换为单行格式（禁止使用\\begin{align}等多行环境）\n4. 多行公式用空格分隔或合并为单行\n5. 不添加解释性文字，直接输出纯净的LaTeX代码"
            }

            # 保存配置
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)

            InfoBar.success(
                title="成功",
                content="配置已保存",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
            return True
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"保存配置失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return False

    def test_connection(self):
        """测试API连接"""
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=self.apiKeyEdit.text(),
                base_url=self.apiUrlEdit.text()
            )
            # 发送一个简单的请求测试连接
            response = client.models.list()
            
            InfoBar.success(
                title="成功",
                content="API连接测试成功",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title="错误",
                content=f"API连接测试失败: {str(e)}",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )

    def accept(self):
        """点击确定按钮的处理"""
        if self.save_config():
            super().accept() 