import torch
import warnings
import argparse
import logging
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QObject, pyqtSignal, QBuffer, QByteArray, QIODevice
from PIL import Image
from io import BytesIO

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

    def process_pixmap(self, pixmap: QPixmap):
        """直接处理QPixmap对象"""
        try:
            if self.model is None or self.vis_processor is None:
                self.logger.warning("模型尚未加载完成，无法处理QPixmap")
                self.finished.emit("识别失败: 模型尚未加载完成")
                return

            self.logger.info("开始处理QPixmap...")
            # 将QPixmap转换为QImage
            q_image = pixmap.toImage()

            if q_image.isNull():
                raise ValueError("QPixmap转换为QImage失败，结果为null")

            byte_array = QByteArray()
            buffer_device = QBuffer(byte_array)

            success = False
            try:
                # Open the buffer for writing
                if not buffer_device.open(QIODevice.WriteOnly):
                    raise IOError("无法打开QBuffer进行写入")

                # Ensure the QImage is in a format suitable for saving to PNG
                safe_formats = (
                    QImage.Format_ARGB32,
                    QImage.Format_RGB32,
                    QImage.Format_ARGB32_Premultiplied,
                    QImage.Format_RGB888,
                )
                if q_image.format() not in safe_formats:
                    self.logger.debug(
                        f"将QImage从格式{q_image.format()}转换为Format_ARGB32"
                    )
                    q_image = q_image.convertToFormat(QImage.Format_ARGB32)
                    if q_image.isNull():
                        raise ValueError("QImage格式转换失败")
                else:
                    self.logger.debug(f"QImage格式{q_image.format()}适合保存")

                # Save the QImage to the QBuffer as a PNG file
                success = q_image.save(buffer_device, "PNG")

                if not success:
                    raise IOError("无法将QImage保存为PNG到缓冲区")

            finally:
                # Always ensure the buffer is closed
                if buffer_device.isOpen():
                    buffer_device.close()

            # Get the byte array from the buffer after saving
            byte_array_data = byte_array.data()
            if not byte_array_data:
                raise IOError("保存QImage后QBuffer中没有数据")

            self.logger.debug(
                f"QImage已保存为PNG到QBuffer。缓冲区大小: {len(byte_array_data)}字节"
            )

            # Open the image from the buffer using PIL
            buffer = BytesIO(byte_array_data)
            pil_image = Image.open(buffer)
            pil_image = pil_image.convert("RGB")

            self.logger.debug(
                f"QPixmap已通过QBuffer转换为PIL Image。尺寸: {pil_image.size}, 模式: {pil_image.mode}"
            )

            # Process the image using the visual processor
            image_tensor = self.vis_processor(pil_image).unsqueeze(0).to(self.device)
            self.logger.debug("PIL Image已通过视觉处理器处理")

            # Perform inference
            with torch.no_grad():
                output = self.model.generate({"image": image_tensor})
            self.logger.debug("模型推理完成")

            result = output["pred_str"][0]
            self.logger.info(f"QPixmap识别结果:\n{result}")
            self.finished.emit(result)

        except Exception as e:
            error_msg = f"识别失败 (pixmap): {str(e)}"
            self.logger.error(error_msg)
            import traceback

            self.logger.error(traceback.format_exc())
            self.finished.emit(error_msg)
