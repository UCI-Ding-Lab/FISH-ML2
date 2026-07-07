import pathlib


def build_backend(mode: str, config_path: pathlib.Path):
    """Build the requested backend for one GUI session."""
    if mode == "gdino_sam":
        from .gdino_sam_backend import GdinoSamBackend
        return GdinoSamBackend(config_path)
    from .cellpose_backend import CellposeBackend
    return CellposeBackend(config_path)
