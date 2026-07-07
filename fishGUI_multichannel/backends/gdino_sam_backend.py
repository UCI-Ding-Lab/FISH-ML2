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
        return self._core.AppIntPREDICTwrapper(nucleus_img, bbox_list)

    def predict_cytoplasm(self, model_input):
        return self._core.AppIntPREDICTwrapper(model_input)
