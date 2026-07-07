import pathlib
import numpy as np
import fishCore


class CellposeBackend:
    """Wrap the current Cellpose-SAM backend behind a simple shared API."""

    def __init__(self, config_path: pathlib.Path, backend_role: str = "backend"):
        """Create one Cellpose-SAM backend for a specific GUI role."""
        self._core = fishCore.Fish(config_path, backend_role)

    @property
    def device(self):
        return self._core.device

    @property
    def config(self):
        return self._core.config

    def generate_bboxes(self, nucleus_img):
        return self._core.AppIntDINOwrapper(nucleus_img)

    def predict_nucleus(self, nucleus_img, bbox_list=None):
        """Segment nuclei without using bbox prompts."""
        _ = bbox_list
        nucleus_img = np.stack([nucleus_img, nucleus_img, nucleus_img], axis=-1).astype(np.float32, copy=False)
        return self._core.predict(nucleus_img)

    def predict_cytoplasm(self, model_input):
        """Segment cytoplasm using the current Cellpose-SAM path."""
        return self._core.predict(model_input)
