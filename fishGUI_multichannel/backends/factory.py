import pathlib


def build_backend(mode: str, config_path: pathlib.Path, backend_role: str = "backend"):
    """Build the requested backend for one GUI role in the session."""
    if mode == "gdino_sam":
        from .gdino_sam_backend import GdinoSamBackend
        return GdinoSamBackend(config_path, backend_role)
    from .cellpose_backend import CellposeBackend
    return CellposeBackend(config_path, backend_role)
