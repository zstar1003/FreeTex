import torch
import warnings
import argparse
import logging
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QObject, pyqtSignal, QBuffer, QByteArray, QIODevice
from PIL import Image
from io import BytesIO
import cv2
import numpy as np
import json

warnings.filterwarnings("ignore")


class LocalProcessor(QObject):
    """
    本地图像处理器，使用QObject以便在QThread中运行
    功能：
    1. 加载本地模型进行图像识别
    2. 通过信号返回识别结果
    """

    finished = pyqtSignal(str)  # 识别完成信号
    model_loaded = pyqtSignal(str)  # 模型加载完成信号，附带设备信息

    def __init__(self, cfg_path):
        """
        初始化处理器，但不立即加载模型。
        模型加载将在moveToThread并启动线程后，通过start_loading方法触发。
        """
        super().__init__()
        self.cfg_path = cfg_path
        self.model = None
        self.vis_processor = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger = logging.getLogger("logs/FreeTex.log")
        self.logger.debug(f"LocalProcessor 初始化完成. 使用设备: {self.device}")

    def start_loading(self):
        """
        在线程启动后调用此方法来加载模型。
        """
        self.logger.info("开始加载模型...")
        try:
            self.init_model()
            if self.model:
                self.model.eval()
                self.logger.debug("模型已设置为评估模式")
            # 发射模型加载完成信号，传递设备信息
            self.model_loaded.emit(str(self.device))
            self.logger.info("模型加载完成")
        except Exception as e:
            # 如果加载失败，发射模型加载完成信号带有错误信息
            error_msg = f"模型加载失败: {str(e)}"
            self.logger.error(error_msg)
            self.model_loaded.emit(f"加载失败 ({str(self.device)}): {str(e)}")

    def init_model(self):
        """初始化模型"""
        self.logger.debug("执行init_model...")
        import unimernet.tasks as tasks
        from unimernet.common.config import Config
        from unimernet.processors import load_processor

        self.logger.info(f"在设备上初始化模型: {self.device}")

        args = argparse.Namespace(cfg_path=self.cfg_path, options=None)
        cfg = Config(args)

        task = tasks.setup_task(cfg)
        # Load model and move to device
        self.model = task.build_model(cfg).to(self.device)
        self.logger.info("模型已构建并移动到设备")
        # Load processor
        self.vis_processor = load_processor(
            "formula_image_eval",
            cfg.config.datasets.formula_rec_eval.vis_processor.eval,
        )
        self.logger.info("视觉处理器已加载")

    def process_image(self, image_path):
        """
        处理图像并返回LaTeX公式
        参数:
            image_path: 图像路径
        """
        try:
            if self.model is None or self.vis_processor is None:
                self.logger.warning("模型尚未加载完成，无法处理图像")
                self.finished.emit("识别失败: 模型尚未加载完成")
                return

            self.logger.info(f"正在处理图像路径: {image_path}")
            raw_image = Image.open(image_path).convert("RGB")  # Ensure RGB
            image_tensor = self.vis_processor(raw_image).unsqueeze(0).to(self.device)
            self.logger.debug("图像已通过视觉处理器处理")

            with (
                torch.no_grad()
            ):  # Inference should be done without gradient calculation
                output = self.model.generate({"image": image_tensor})
            self.logger.debug("模型推理完成")

            result = output["pred_str"][0]
            self.logger.info(f"路径识别结果:\n{result}")
            self.finished.emit(result)
        except Exception as e:
            error_msg = f"识别失败 (路径): {str(e)}"
            self.logger.error(error_msg)
            self.finished.emit(error_msg)

    def preprocess_image(self, pixmap):
        """
        预处理图像，检测背景色并在必要时进行颜色反转
        
        Args:
            pixmap: QPixmap对象
            
        Returns:
            处理后的QPixmap对象
        """
        # 将QPixmap转换为numpy数组
        image = self._pixmap_to_cv2(pixmap)
        if image is None:
            return pixmap

        # 计算图像的平均亮度
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        
        # 如果平均亮度小于128（暗色背景），进行颜色反转
        if mean_brightness < 128:
            self.logger.info(f"检测到深色背景（平均亮度：{mean_brightness}），进行颜色反转")
            # 反转图像
            image = cv2.bitwise_not(image)
            # 转回QPixmap
            return self._cv2_to_pixmap(image)
        
        self.logger.info(f"检测到浅色背景（平均亮度：{mean_brightness}），无需处理")
        return pixmap

    def _pixmap_to_cv2(self, pixmap):
        """
        将QPixmap转换为OpenCV格式
        """
        try:
            # 转换QPixmap为QImage
            image = pixmap.toImage()
            # 获取图像数据
            width = image.width()
            height = image.height()
            ptr = image.bits()
            ptr.setsize(height * width * 4)
            # 转换为numpy数组
            arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
            # 转换为BGR格式
            return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            self.logger.error(f"图像转换失败: {str(e)}")
            return None

    def _cv2_to_pixmap(self, cv_img):
        """
        将OpenCV图像转换为QPixmap
        """
        try:
            # 转换为RGB格式
            rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            # 创建QImage
            height, width, channel = rgb_image.shape
            bytes_per_line = 3 * width
            q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            # 转换为QPixmap
            return QPixmap.fromImage(q_image)
        except Exception as e:
            self.logger.error(f"图像转换失败: {str(e)}")
            return None

    def process_pixmap(self, pixmap):
        """处理QPixmap图像"""
        try:
            if self.model is None or self.vis_processor is None:
                self.finished.emit("模型未加载，无法处理图像")
                return

            # 预处理图像
            processed_pixmap = self.preprocess_image(pixmap)
            if processed_pixmap is None:
                self.finished.emit("图像预处理失败")
                return

            # 将QPixmap转换为PIL Image用于模型处理
            pil_image = self._pixmap_to_pil(processed_pixmap)
            if pil_image is None:
                self.finished.emit("图像转换失败")
                return

            # 检查是否启用多模态识别
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    model_config = config.get("model_config", {})
                    if model_config.get("enabled", False):
                        # 使用多模态识别
                        result = self._process_with_multimodal(pil_image, model_config)
                    else:
                        # 使用本地模型识别
                        image_tensor = self.vis_processor(pil_image).unsqueeze(0).to(self.device)
                        with torch.no_grad():
                            output = self.model.generate({"image": image_tensor})
                        result = output["pred_str"][0]
            except Exception as e:
                self.logger.error(f"配置读取失败，使用本地模型: {str(e)}")
                # 使用本地模型识别
                image_tensor = self.vis_processor(pil_image).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    output = self.model.generate({"image": image_tensor})
                result = output["pred_str"][0]

            self.logger.info(f"识别结果: {result}")
            self.finished.emit(result)

        except Exception as e:
            self.logger.error(f"图像处理失败: {str(e)}")
            self.finished.emit(f"识别失败: {str(e)}")

    def _process_with_multimodal(self, image, config):
        """使用多模态模型处理图像"""
        import base64
        from io import BytesIO
        from openai import OpenAI

        # 将PIL Image转换为base64
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # 创建OpenAI客户端
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["api_url"]
        )

        # 准备消息
        messages = [
            {"role": "system", "content": config.get("system_prompt", "")},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    },
                    {"type": "text", "text": "请将图中的数学公式转换为精确的单行LaTeX代码，禁止使用多行环境，不要添加任何额外描述。"}
                ]
            }
        ]

        # 发送请求
        response = client.chat.completions.create(
            model=config["model_name"],
            messages=messages,
            max_tokens=1024,
            temperature=0.2
        )

        # 后处理
        latex_code = response.choices[0].message.content
        latex_code = latex_code.replace("\\begin{align}", "").replace("\\end{align}", "")
        latex_code = latex_code.replace("\\begin{aligned}", "").replace("\\end{aligned}", "")
        latex_code = " ".join(latex_code.split())  # 合并多余空格

        return latex_code

    def _pixmap_to_pil(self, pixmap):
        """
        将QPixmap转换为PIL Image
        """
        try:
            # 转换QPixmap为QImage
            image = pixmap.toImage()
            # 获取图像数据
            width = image.width()
            height = image.height()
            ptr = image.bits()
            ptr.setsize(height * width * 4)
            # 转换为numpy数组
            arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
            # 转换为RGB格式
            rgb_array = cv2.cvtColor(arr, cv2.COLOR_BGRA2RGB)
            # 转换为PIL Image
            return Image.fromarray(rgb_array)
        except Exception as e:
            self.logger.error(f"图像转换失败: {str(e)}")
            return None
