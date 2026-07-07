import pathlib
import fishCore_gdino_sam


class GdinoSamBackend:
    """Wrap the prototype GroundingDINO + SAM backend behind the same shared API."""

    def __init__(self, config_path: pathlib.Path):
        self._core = fishCore_gdino_sam.Fish(config_path)

    @property
    def device(self):
        return getattr(self._core, "device", "cpu")

    @property
    def config(self):
        return self._core.config

    def generate_bboxes(self, nucleus_img):
        return self._core.AppIntDINOwrapper(nucleus_img)

    def predict_nucleus(self, nucleus_img, bbox_list=None):
        """Segment nuclei using SAM with bbox prompts when they exist."""
        prompt_boxes = bbox_list if bbox_list else None
        return self._core.AppIntPREDICTwrapper(nucleus_img, prompt_boxes)

    def predict_cytoplasm(self, model_input):
        """Legacy gdino and SAM backend does not support current cytoplasm segmentation flow."""
        raise NotImplementedError(
            "GroundingDINO + SAM prototype currently supports nucleus segmentation only."
        )
