import torch
import warnings
import numpy as np
import argparse
# 导入 QPixmap, QImage
from PyQt5.QtGui import QPixmap, QImage
# 导入 QObject, pyqtSignal, QThread, 以及用于缓冲区的 QBuffer, QByteArray, QIODevice
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QBuffer, QByteArray, QIODevice
from PIL import Image
from io import BytesIO # 导入BytesIO，用于PIL读取

warnings.filterwarnings("ignore")

# Import task/model/processor classes conditionally or later
# import unimernet.tasks as tasks
# from unimernet.common.config import Config
# from unimernet.processors import load_processor

class LocalProcessor(QObject):
    """
    本地图像处理器，使用QObject以便在QThread中运行
    功能：
    1. 加载本地模型进行图像识别
    2. 通过信号返回识别结果
    """
    finished = pyqtSignal(str)  # 识别完成信号
    model_loaded = pyqtSignal(str) # 模型加载完成信号，附带设备信息

    def __init__(self, cfg_path):
        """
        初始化处理器，但不立即加载模型。
        模型加载将在moveToThread并启动线程后，通过start_loading方法触发。
        """
        super().__init__()
        self.cfg_path = cfg_path
        self.model = None
        self.vis_processor = None
        # 确定设备，但模型加载和device.cuda()操作留在 start_loading 中
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"LocalProcessor initialized. Target device: {self.device}") # Debug print

    def start_loading(self):
        """
        在线程启动后调用此方法来加载模型。
        """
        print("Starting model loading...") # Debug print
        try:
            self.init_model()
            # Set model to evaluation mode after loading
            if self.model:
                self.model.eval()
                print("Model set to eval mode.") # Debug print
            # 发射模型加载完成信号，传递设备信息
            self.model_loaded.emit(str(self.device))
            print("Model loading finished.") # Debug print
        except Exception as e:
            # 如果加载失败，发射模型加载完成信号带有错误信息
            error_msg = f"模型加载失败: {str(e)}"
            print(error_msg) # Debug print
            self.model_loaded.emit(f"加载失败 ({str(self.device)}): {str(e)}") # Notify failure with device info and error
            # Also notify the finished state with error
            # self.finished.emit(error_msg) # Maybe not necessary, model_loaded indicates failure

    def init_model(self):
        """初始化模型 - 这个方法现在只负责实际加载逻辑"""
        print("Executing init_model...") # Debug print
        # 确保在这里导入，避免在主线程初始化时引入torch/model dependencies too early if possible
        import unimernet.tasks as tasks
        from unimernet.common.config import Config
        from unimernet.processors import load_processor

        # Re-check device here just in case (though __init__ sets it)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Initializing model on device: {self.device}") # Debug print

        args = argparse.Namespace(cfg_path=self.cfg_path, options=None)
        cfg = Config(args)

        # Print config/model paths for debugging
        # print(f"Model config path: {cfg.config.model.get('checkpoint', 'N/A')}")

        task = tasks.setup_task(cfg)
        # Load model and move to device
        self.model = task.build_model(cfg).to(self.device)
        print("Model built and moved to device.") # Debug print

        # Load processor
        self.vis_processor = load_processor('formula_image_eval',
                                           cfg.config.datasets.formula_rec_eval.vis_processor.eval)
        print("Visual processor loaded.") # Debug print

        # Optional: Run a dummy inference to warm up (might take time)
        # from PIL import Image
        # print("Running dummy inference for warmup...")
        # try:
        #     dummy_img = Image.new('RGB', (100, 100), color = 'red')
        #     dummy_input = self.vis_processor(dummy_img).unsqueeze(0).to(self.device)
        #     with torch.no_grad():
        #         _ = self.model.generate({"image": dummy_input})
        #     print("Dummy inference finished.")
        # except Exception as e:
        #      print(f"Dummy inference failed: {e}")


    def process_image(self, image_path):
        """
        处理图像并返回LaTeX公式
        参数:
            image_path: 图像路径
        """
        # Use try-except within the thread method itself
        try:
            if self.model is None or self.vis_processor is None:
                print("Model not loaded yet, cannot process image_path.") # Debug print
                self.finished.emit("识别失败: 模型尚未加载完成")
                return

            print(f"Processing image from path: {image_path}") # Debug print
            raw_image = Image.open(image_path).convert("RGB") # Ensure RGB
            image_tensor = self.vis_processor(raw_image).unsqueeze(0).to(self.device)
            print("Image processed by visual processor.") # Debug print

            with torch.no_grad(): # Inference should be done without gradient calculation
                 output = self.model.generate({"image": image_tensor})
            print("Model inference complete.") # Debug print

            result = output["pred_str"][0]
            print(f'Recognition result for path:\n{result}') # Debug print
            self.finished.emit(result)
        except Exception as e:
            error_msg = f"识别失败 (path): {str(e)}"
            print(error_msg) # Debug print
            # import traceback; traceback.print_exc() # Uncomment for detailed traceback
            self.finished.emit(error_msg)

    def process_pixmap(self, pixmap: QPixmap):
        """直接处理QPixmap对象"""
        # Use try-except within the thread method itself
        try:
            if self.model is None or self.vis_processor is None:
                print("Model not loaded yet, cannot process pixmap.") # Debug print
                self.finished.emit("识别失败: 模型尚未加载完成")
                return

            print("Starting QPixmap processing...") # Debug print
            # 将QPixmap转换为QImage
            q_image = pixmap.toImage()

            # Check for null image after conversion
            if q_image.isNull():
                 raise ValueError("QPixmap to QImage conversion resulted in a null image.")

            # --- Start: Convert QImage to PIL Image using QBuffer ---
            byte_array = QByteArray()
            buffer_device = QBuffer(byte_array)

            success = False
            try:
                # Open the buffer for writing
                if not buffer_device.open(QIODevice.WriteOnly):
                     raise IOError("Failed to open QBuffer for writing.")

                # Ensure the QImage is in a format suitable for saving to PNG (or another format PIL can read)
                # Convert to a format that PIL can reliably read from PNG (e.g., ARGB32 or RGB32 or RGB888)
                safe_formats = (QImage.Format_ARGB32, QImage.Format_RGB32, QImage.Format_ARGB32_Premultiplied, QImage.Format_RGB888)
                if q_image.format() not in safe_formats:
                     print(f"Converting QImage from format {q_image.format()} to Format_ARGB32 for saving.")
                     q_image = q_image.convertToFormat(QImage.Format_ARGB32)
                     if q_image.isNull():
                          raise ValueError("QImage format conversion failed.")
                else:
                     print(f"QImage format {q_image.format()} is suitable for saving.")


                # Save the QImage to the QBuffer as a PNG file
                # Pass the QBuffer instance as the device
                # The second argument is the format name (e.g., "PNG", "JPG")
                success = q_image.save(buffer_device, "PNG")

                if not success:
                    raise IOError("Failed to save QImage to buffer as PNG.")

            finally:
                # Always ensure the buffer is closed
                if buffer_device.isOpen():
                     buffer_device.close()

            # Get the byte array from the buffer after saving
            byte_array_data = byte_array.data()
            if not byte_array_data: # Check if data was actually written
                 raise IOError("QBuffer contains no data after saving QImage.")

            print(f"QImage saved to QBuffer as PNG. Buffer size: {len(byte_array_data)} bytes.") # Debug print

            # Open the image from the buffer using PIL
            # Use BytesIO to wrap the byte array data
            buffer = BytesIO(byte_array_data)
            pil_image = Image.open(buffer)

            # Convert PIL image to RGB (most models expect 3 channels)
            # Use .convert("RGB") for standard models or .convert("RGBA") if alpha is needed
            # Formula models usually don't need alpha, RGB is safer
            # We convert *after* opening with PIL to handle potential alpha channels correctly
            pil_image = pil_image.convert("RGB")

            print(f"QPixmap converted to PIL Image via QBuffer. Size: {pil_image.size}, Mode: {pil_image.mode}") # Debug print
            # --- End: Convert QImage to PIL Image using QBuffer ---


            # Process the image using the visual processor
            image_tensor = self.vis_processor(pil_image).unsqueeze(0).to(self.device)
            print("PIL Image processed by visual processor.") # Debug print

            # Perform inference
            with torch.no_grad(): # Inference should be done without gradient calculation
                output = self.model.generate({"image": image_tensor})
            print("Model inference complete.") # Debug print

            result = output["pred_str"][0]
            print(f'Recognition result for pixmap:\n{result}') # Debug print
            self.finished.emit(result)

        except Exception as e:
            error_msg = f"识别失败 (pixmap): {str(e)}"
            print(error_msg) # Debug print
            import traceback # Import traceback for detailed error output
            traceback.print_exc() # Print traceback for debugging
            self.finished.emit(error_msg)
