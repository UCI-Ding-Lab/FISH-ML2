import pathlib
import fishCore_gdino_sam


class GdinoSamBackend:
    """Wrap the prototype GroundingDINO + SAM backend behind the same shared API."""

    def __init__(self, config_path: pathlib.Path, backend_role: str = "backend"):
        """Create one GroundingDINO and SAM backend for a specific GUI role."""
        self._core = fishCore_gdino_sam.Fish(config_path, backend_role)

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
        """Segment nuclei using SAM with bbox prompts when they exist."""
        prompt_boxes = bbox_list if bbox_list else None
        predictor = self._core.sam_nucleus_predictor
        return predictor.AppIntPREDICTwrapper(nucleus_img, prompt_boxes)

    def predict_cytoplasm(self, model_input):
        """Legacy gdino and SAM backend does not support current cytoplasm segmentation flow."""
        raise NotImplementedError(
            "GroundingDINO + SAM prototype currently supports nucleus segmentation only."
        )
