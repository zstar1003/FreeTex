import torch
import warnings
import numpy as np
import argparse
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QPixmap
from PIL import Image

warnings.filterwarnings("ignore")

class LocalProcessor(QObject):
    """
    本地图像处理器，使用QObject以便在QThread中运行
    功能：
    1. 加载本地模型进行图像识别
    2. 通过信号返回识别结果
    """
    finished = pyqtSignal(str)  # 识别完成信号
    
    def __init__(self, cfg_path):
        super().__init__()
        self.cfg_path = cfg_path
        self.model = None
        self.vis_processor = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.init_model()
        
    def init_model(self):
        """初始化模型"""
        import unimernet.tasks as tasks
        from unimernet.common.config import Config
        from unimernet.processors import load_processor
        
        args = argparse.Namespace(cfg_path=self.cfg_path, options=None)
        cfg = Config(args)
        task = tasks.setup_task(cfg)
        self.model = task.build_model(cfg).to(self.device)
        self.vis_processor = load_processor('formula_image_eval', 
                                           cfg.config.datasets.formula_rec_eval.vis_processor.eval)
    
    def process_image(self, image_path):
        """
        处理图像并返回LaTeX公式
        参数:
            image_path: 图像路径
        """
        try:
            raw_image = Image.open(image_path)
            image = self.vis_processor(raw_image).unsqueeze(0).to(self.device)
            output = self.model.generate({"image": image})
            self.finished.emit(output["pred_str"][0])
        except Exception as e:
            self.finished.emit(f"识别失败: {str(e)}")

    def process_pixmap(self, pixmap: QPixmap):
        """直接处理QPixmap对象"""
        try:
            print("开始处理")
            # 将QPixmap转换为PIL Image
            image = pixmap.toImage()
            byte_array = image.bits().asstring(image.byteCount())
            pil_image = Image.frombytes("RGBA", (image.width(), image.height()), byte_array)
            # 处理图像
            image = self.vis_processor(pil_image).unsqueeze(0).to(self.device)
            output = self.model.generate({"image": image})
            result = output["pred_str"][0]
            print(f'识别结果:\n{result}')
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit(f"识别失败: {str(e)}")
            print(e)