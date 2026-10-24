import pathlib
import numpy as np
from core import fishCore_gdino_sam


class GdinoSamBackend:
    """Wrap the prototype GroundingDINO + SAM backend behind the same shared API."""

    def __init__(self, config_path: pathlib.Path, backend_role: str = "backend"):
        """Create one GroundingDINO and SAM backend for a specific GUI role."""
        self._core = fishCore_gdino_sam.Fish(config_path, backend_role)
        self._load_default_nucleus_model()

    def _load_default_nucleus_model(self) -> None:
        """Load the legacy SAM nucleus weights expected by the old GDINO workflow."""
        self._core.set_model_version("3.50")

    @property
    def device(self):
        """Return the compute device string used by the legacy backend."""
        device_name = self._core.device
        if device_name is None:
            return "cpu"
        return device_name

    @property
    def config(self):
        return self._core.config

    def generate_bboxes(self, nucleus_img):
        return self._core.AppIntDINOwrapper(nucleus_img)

    def predict_nucleus(self, nucleus_img, bbox_list=None):
        """Segment nuclei using SAM, prompted by the frame's reviewed boxes."""
        if not bbox_list:
            # Boxes are always made before segmenting, so no boxes means the user removed them all
            height, width = np.shape(nucleus_img)[:2]
            return np.zeros((0, height, width), dtype=np.uint8)
        predictor = self._core.sam_nucleus_predictor
        return predictor.AppIntPREDICTwrapper(nucleus_img, bbox_list)

    def predict_cytoplasm(self, model_input):
        """Legacy gdino and SAM backend does not support current cytoplasm segmentation flow."""
        raise NotImplementedError(
            "GroundingDINO + SAM prototype currently supports nucleus segmentation only."
        )
