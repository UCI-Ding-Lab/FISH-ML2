import pathlib

from .cellpose_backend import CellposeBackend
from .gdino_sam_backend import GdinoSamBackend


def build_backend(mode: str, config_path: pathlib.Path):
    """Build the requested backend for one GUI session."""
    if mode == "gdino_sam":
        return GdinoSamBackend(config_path)
    return CellposeBackend(config_path)
