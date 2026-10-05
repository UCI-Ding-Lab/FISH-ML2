from .export_cell_data import frame_has_whole_cell_masks

NUCLEUS_ONLY = "nucleus_only"
WHOLE_CELL_ONLY = "whole_cell_only"
BOTH = "both"

EXPORT_MODE_LABELS = {
    NUCLEUS_ONLY: "Nucleus only",
    WHOLE_CELL_ONLY: "Whole-cell only",
    BOTH: "Both (paired)",
}


def guess_export_mode(frames: list, last_mode: str | None = None) -> str:
    """
    Pick the export mode the popup starts on.
    Uses the last choice when there is one; otherwise looks at what the selected frames have.
    """
    if last_mode is not None:
        return last_mode
    selected = [frame for frame in frames if frame.selected]
    has_nuclei = any(frame.has_nucleus_segments() for frame in selected)
    has_whole_cells = any(frame_has_whole_cell_masks(frame) for frame in selected)
    if has_nuclei and not has_whole_cells:
        return NUCLEUS_ONLY
    if has_whole_cells and not has_nuclei:
        return WHOLE_CELL_ONLY
    return BOTH
