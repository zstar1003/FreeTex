from unimernet.common.registry import registry
from omegaconf import OmegaConf
import albumentations as alb
from albumentations.pytorch import ToTensorV2
from unimernet.processors.base_processor import BaseProcessor
import numpy as np
import cv2
from PIL import Image, ImageOps
from torchvision.transforms.functional import resize
import random


class FormulaImageBaseProcessor(BaseProcessor):

    def __init__(self, image_size):
        super(FormulaImageBaseProcessor, self).__init__()
        self.input_size = [int(_) for _ in image_size]
        assert len(self.input_size) == 2

    @staticmethod
    def crop_margin(img: Image.Image) -> Image.Image:
        data = np.array(img.convert("L"))
        data = data.astype(np.uint8)
        max_val = data.max()
        min_val = data.min()
        if max_val == min_val:
            return img
        data = (data - min_val) / (max_val - min_val) * 255
        gray = 255 * (data < 200).astype(np.uint8)

        coords = cv2.findNonZero(gray)  # Find all non-zero points (text)
        a, b, w, h = cv2.boundingRect(coords)  # Find minimum spanning bounding box
        return img.crop((a, b, w + a, h + b))

    def prepare_input(self, img: Image.Image, random_padding: bool = False):
        """
        Convert PIL Image to tensor according to specified input_size after following steps below:
            - resize
            - rotate (if align_long_axis is True and image is not aligned longer axis with canvas)
            - pad
        """
        if img is None:
            return
        # crop margins
        try:
            img = self.crop_margin(img.convert("RGB"))
        except OSError:
            # might throw an error for broken files
            return

        if img.height == 0 or img.width == 0:
            return

        img = resize(img, min(self.input_size))
        img.thumbnail((self.input_size[1], self.input_size[0]))
        delta_width = self.input_size[1] - img.width
        delta_height = self.input_size[0] - img.height
        if random_padding:
            pad_width = np.random.randint(low=0, high=delta_width + 1)
            pad_height = np.random.randint(low=0, high=delta_height + 1)
        else:
            pad_width = delta_width // 2
            pad_height = delta_height // 2
        padding = (
            pad_width,
            pad_height,
            delta_width - pad_width,
            delta_height - pad_height,
        )
        return ImageOps.expand(img, padding)


@registry.register_processor("formula_image_train")
class FormulaImageTrainProcessor(FormulaImageBaseProcessor):
    def __init__(self, image_size=384):
        super().__init__(image_size)

        # Import weather-related augmentations only when initializing this class
        from unimernet.processors.formula_processor_helper.nougat import Bitmap, Dilation, Erosion
        from unimernet.processors.formula_processor_helper.weather import Fog, Frost, Snow, Rain, Shadow

        self.transform = alb.Compose(
            [
                alb.Compose(
                    [
                        Bitmap(p=0.05),
                        alb.OneOf([Fog(), Frost(), Snow(), Rain(), Shadow()], p=0.2),
                        alb.OneOf([Erosion((2, 3)), Dilation((2, 3))], p=0.2),
                        alb.ShiftScaleRotate(shift_limit=0, scale_limit=(-.15, 0), rotate_limit=1, border_mode=0,
                                             interpolation=3,
                                             value=[255, 255, 255],
                                             p=1),
                        alb.GridDistortion(distort_limit=0.1, border_mode=0, interpolation=3, value=[255, 255, 255],
                                           p=.5)],
                    p=.15),
                # alb.InvertImg(p=.15),
                alb.RGBShift(r_shift_limit=15, g_shift_limit=15, b_shift_limit=15, p=0.3),
                alb.GaussNoise(10, p=.2),
                alb.RandomBrightnessContrast(.05, (-.2, 0), True, p=0.2),
                alb.ImageCompression(95, p=.3),
                alb.ToGray(always_apply=True),
                alb.Normalize((0.7931, 0.7931, 0.7931), (0.1738, 0.1738, 0.1738)),
                # alb.Sharpen()
                ToTensorV2(),
            ]
        )

    def __call__(self, item):
        img = self.prepare_input(item, random_padding=True)
        if img is None:
            return img
        return self.transform(image=np.array(img))['image'][:1]

    @classmethod
    def from_config(cls, cfg=None):
        if cfg is None:
            cfg = OmegaConf.create()

        image_size = cfg.get("image_size", [384, 384])

        return cls(
            image_size=image_size,
        )


@registry.register_processor("formula_image_multi_scale_train")
class FormulaImageMultiScaleTrainProcessor(FormulaImageTrainProcessor):
    def __init__(self, all_scales):
        for i, scales in enumerate(all_scales):
            all_scales[i] = [int(_) for _ in scales]
        super(FormulaImageMultiScaleTrainProcessor, self).__init__(all_scales[0])
        self.all_scales = all_scales

    @classmethod
    def from_config(cls, cfg=None):
        if cfg is None:
            cfg = OmegaConf.create()

        all_scales = cfg.get("all_scales", [[384, 384]])
        return cls(
            all_scales=all_scales
        )

    def reset_scale(self):
        self.input_size = random.choice(self.all_scales)


@registry.register_processor("formula_image_eval")
class FormulaImageEvalProcessor(FormulaImageBaseProcessor):
    def __init__(self, image_size):
        super().__init__(image_size)

        self.transform = alb.Compose(
            [
                alb.ToGray(always_apply=True),
                alb.Normalize((0.7931, 0.7931, 0.7931), (0.1738, 0.1738, 0.1738)),
                # alb.Sharpen()
                ToTensorV2(),
            ]
        )

    def __call__(self, item):
        image = self.prepare_input(item)
        return self.transform(image=np.array(image))['image'][:1]

    @classmethod
    def from_config(cls, cfg=None):
        if cfg is None:
            cfg = OmegaConf.create()

        image_size = cfg.get("image_size", [384, 384])

        return cls(image_size=image_size)
