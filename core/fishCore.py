# Standard Library Imports
import os
import pathlib
import logging
import configparser
from typing import Tuple

# Third-Party Imports
import numpy as np
import torch
import certifi
from PIL import Image
import cv2
from cellpose import models
from torchvision.ops import box_convert

# Local Application/Library Specific Imports
import groundingdino.datasets.transforms as T
import groundingdino.util.inference as dino
import groundingdino

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',
        'INFO': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[1;91m',
        'RESET': '\033[0m'
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        record.levelname = f"{log_color}{record.levelname}{reset_color}"
        record.msg = f"{log_color}{record.msg}{reset_color}"
        return super().format(record)


def _build_console_handler() -> logging.StreamHandler:
    """Create one console handler for the shared fishcore logger."""
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = ColoredFormatter("[%(asctime)s][%(levelname)s] %(message)s")
    console_handler.setFormatter(formatter)
    return console_handler


def _has_fishcore_console_handler(logger: logging.Logger) -> bool:
    """Return True when the shared fishcore console handler already exists."""
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            return True
    return False

class Fish():
    def __init__(self, config: pathlib.Path, backend_role: str = "backend") -> None:
        """Create one Cellpose-SAM core for a specific segmentation role."""
        self.backend_role = backend_role
        self.setup__config(config)
        self.setup__logger()
        self.setup__asset()
        self.setup__ai()
    
    def setup__config(self, config):
        self.config_path = pathlib.Path(config).resolve()
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)
    def setup__logger(self):
        self.logger = logging.getLogger('fishcore')
        self.logger.setLevel(logging.INFO)
        if not _has_fishcore_console_handler(self.logger):
            self.logger.addHandler(_build_console_handler())
        loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
        for logger in loggers:
            if "transformers" in logger.name.lower():
                logger.setLevel(logging.ERROR)
    def _role_text(self) -> str:
        """Return a readable role label for startup log messages."""
        return self.backend_role.replace("_", " ").title()
    def setup__asset(self): # TODO update this : SAM -> Cellpose-SAM after testing similar to table in readme is completed
        asset_folder_path = pathlib.Path(self.config["general"]["asset_folder_path"])
        model_folder_path = pathlib.Path(self.config["general"]["model_folder_path"])
        if not asset_folder_path.is_absolute():
            asset_folder_path = (self.config_path.parent / asset_folder_path).resolve()
        if not model_folder_path.is_absolute():
            model_folder_path = (self.config_path.parent / model_folder_path).resolve()
        self.asset_folder_path = asset_folder_path
        self.model_folder_path = model_folder_path
        self.supported_version = self.config["general"]["supported_version"].split(",")
        self.model_version = None
        self.model_path = None
    def setup__ai(self):
        self._configure_ssl_certs()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.logger.info(
            "%s backend: torch=%s cuda_available=%s cuda_version=%s selected_device=%s",
            self._role_text(),
            torch.__version__,
            torch.cuda.is_available(),
            torch.version.cuda,
            self.device,
        )
        if self.device == "cuda":
            self.logger.info("%s CUDA device: %s", self._role_text(), torch.cuda.get_device_name(0))
        else:
            self.logger.warning(
                "%s backend is running on CPU. Install a CUDA-enabled PyTorch build in this environment to use the GPU.",
                self._role_text(),
            )
        self.model = models.CellposeModel(gpu=(self.device == "cuda"))
        checkpoint_path = self.model_folder_path / self.config["cellpose_sam"]["checkpoint"]
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        self.model.net.load_state_dict(checkpoint["state_dict"]) # load weights
        self.model.net.eval() # Ensure inference is deterministic and consistent : dropout is turned off & BatchNorm uses average during training 
        self.eval_diam = checkpoint["eval_diam"] # set eval_diam (hyperparameter) to the average mask diameter of GT labels in training set
        self.model_version = "cellpose-sam"
        self.model_path = checkpoint_path
        self.logger.info("%s Cellpose-SAM model loaded. eval_diam=%s", self._role_text(), self.eval_diam)
        self.gdino_config = pathlib.Path(groundingdino.__path__[0]) / self.config["dino"]["config"]
        repo_gdino_weights = self.model_folder_path / self.config["dino"]["weights"]
        package_gdino_weights = pathlib.Path(groundingdino.__path__[0]) / self.config["dino"]["weights"]
        self.gdino_weights = repo_gdino_weights if repo_gdino_weights.exists() else package_gdino_weights
        self.gdino_model = dino.load_model(self.gdino_config, self.gdino_weights, device=self.device)

    @staticmethod
    def _configure_ssl_certs():
        cert_path = certifi.where()
        for env_name in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
            current_value = os.environ.get(env_name)
            if not current_value or not pathlib.Path(current_value).exists():
                os.environ[env_name] = cert_path

    def set_model_version(self, v: str):
        # Legacy compatibility shim: Fish now always uses Cellpose-SAM.
        self.logger.warning(
            "Ignoring legacy set_model_version(%s); Fish already loaded Cellpose-SAM from %s",
            v,
            self.model_path,
        )
        return self

    def predict(self, img: np.ndarray, diameter=None, flow_threshold=0.4, cellprob_threshold=0.0): # TODO currently flowthreshod and cellprob_threshold are hardcoded -- perhaps allow users to adjust it in the gui
        if img.dtype != np.float32: # expected input image format is float32
            img = img.astype(np.float32)
        if diameter is None:
            diameter = self.eval_diam
        kwargs = dict(
            diameter=diameter,
            flow_threshold=flow_threshold,
            cellprob_threshold=cellprob_threshold,
        )
        masks, flows, styles = self.model.eval(img, **kwargs)
        return masks, flows
    

    # TODO -- 3/31 : check and confirm all methods below 
    @staticmethod
    def helper__hdr2Rgb(hdr_image: np.ndarray, dynamic_range: int) -> np.ndarray:
        scale_factor = 255 / dynamic_range
        scaled_image = (hdr_image * scale_factor).astype(np.uint8)
        rgb_image = np.stack((scaled_image,) * 3, axis=-1)
        return rgb_image
    @staticmethod
    def helper__hdr2RgbNorm(hdr_image: np.ndarray, brightness_factor: int) -> np.ndarray:
        img_normalized = cv2.normalize(hdr_image, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        img_rgb = cv2.cvtColor(img_normalized, cv2.COLOR_GRAY2RGB)
        return np.clip(img_rgb * brightness_factor, 0, 255).astype(np.uint8)
    @staticmethod
    def helper__rectArea(rect):
        x1, y1, x2, y2 = rect
        return (x2 - x1) * (y2 - y1)
    @staticmethod
    def helper__computeIntersectionArea(rect1, rect2):
        x1, y1, x2, y2 = rect1
        x3, y3, x4, y4 = rect2
        xi1 = max(x1, x3)
        yi1 = max(y1, y3)
        xi2 = min(x2, x4)
        yi2 = min(y2, y4)
        if xi1 < xi2 and yi1 < yi2:
            return (xi2 - xi1) * (yi2 - yi1)
        else:
            return 0

    @staticmethod
    def helper__filterAlgorithm(image_source: np.ndarray, boxes: torch.Tensor) -> list:
        h, w, _ = image_source.shape
        boxes = boxes * torch.Tensor([w, h, w, h])
        xyxy = box_convert(boxes=boxes, in_fmt="cxcywh", out_fmt="xyxy").numpy().astype(np.uint16).tolist()
        bboxes = []
        
        # Filtering bounding boxes based on area and size constraints
        for box in xyxy:
            min_x, min_y, max_x, max_y = box
            area = (max_x - min_x) * (max_y - min_y)
            
            # Skip boxes with area too small or too large
            if area < 800 or area > 100000:
                continue
            # Skip boxes with width or height too small
            if max_x - min_x < 40 or max_y - min_y < 40:
                continue
            # Skip boxes near the image edges (within 4 pixels)
            if min_x <= 4 or min_y <= 4 or max_x >= w - 4 or max_y >= h - 4:
                continue
            
            bboxes.append(box)
        
        rects = np.array(bboxes)
        N = len(rects)
        to_delete = set()
        areas = np.array([Fish.helper__rectArea(rect) for rect in rects])
        
        # Overlap filtering logic
        for i in range(N):
            for j in range(i + 1, N):
                if j in to_delete:
                    continue
                intersection_area = Fish.helper__computeIntersectionArea(rects[i], rects[j])
                if intersection_area >= 0.9 * min(areas[i], areas[j]):
                    if areas[i] > areas[j]:
                        to_delete.add(i)
                    else:
                        to_delete.add(j)
        
        # Final list of filtered bounding boxes
        filtered_rects = [rect for k, rect in enumerate(rects) if k not in to_delete]
        return np.array(filtered_rects).tolist()

    @staticmethod
    def helper__imageTransform4Dino(img: np.ndarray) -> Tuple[np.array, torch.Tensor]:
        transform = T.Compose([T.RandomResize([800], max_size=1333),
                               T.ToTensor(),
                               T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),])
        image_source = Image.fromarray(Fish.helper__hdr2RgbNorm(img, 1))
        image = np.asarray(image_source)
        image_transformed, _ = transform(image_source, None)
        return image, image_transformed
    
    def dino_bbox(self, img: np.ndarray) -> dict:
        image_source, image = Fish.helper__imageTransform4Dino(img)

        TEXT_PROMPT = "white flower"
        BOX_TRESHOLD = 0.07
        TEXT_TRESHOLD = 0.05

        boxes, logits, phrases = dino.predict(
            model=self.gdino_model,
            image=image, 
            caption=TEXT_PROMPT, 
            box_threshold=BOX_TRESHOLD, 
            text_threshold=TEXT_TRESHOLD,
            device=self.device,
        )
        finalized_bboxes = Fish.helper__filterAlgorithm(image_source, boxes)
        return finalized_bboxes
    
    def AppIntDINOwrapper(self, img: np.ndarray) -> list[list]:
        return self.dino_bbox(img)
