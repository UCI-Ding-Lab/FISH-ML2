import pathlib
import fishCore


class CellposeBackend:
    """Wrap the current Cellpose-SAM backend behind a simple shared API."""

    def __init__(self, config_path: pathlib.Path):
        self._core = fishCore.Fish(config_path)

    @property
    def device(self):
        return self._core.device

    @property
    def config(self):
        return self._core.config

    def generate_bboxes(self, nucleus_img):
        return self._core.AppIntDINOwrapper(nucleus_img)

    def predict_nucleus(self, nucleus_img, bbox_list=None):
        return self._core.predict(nucleus_img)

    def predict_cytoplasm(self, model_input):
        return self._core.predict(model_input)
