from .export_cell_data import all_selected_frames_are_dapi_only, frame_has_whole_cell_masks

NUCLEUS_ONLY = "nucleus_only"
WHOLE_CELL_ONLY = "whole_cell_only"
BOTH = "both"

EXPORT_MODE_LABELS = {
    NUCLEUS_ONLY: "Nucleus only",
    WHOLE_CELL_ONLY: "Whole-cell only",
    BOTH: "Both (paired)",
}


def available_export_modes(frames: list) -> list[str]:
    """
    Return the export modes that can work for the selected frames.
    Whole-cell modes need cytoplasm images, so only Nucleus only is left when every selected frame is DAPI-only.
    """
    if all_selected_frames_are_dapi_only(frames):
        return [NUCLEUS_ONLY]
    return list(EXPORT_MODE_LABELS)


def guess_export_mode(frames: list, last_mode: str | None = None) -> str:
    """
    Pick the export mode the popup starts on, always one of the available modes.
    Uses the last choice when it is still available; otherwise looks at what the selected frames have.
    """
    available = available_export_modes(frames)
    if last_mode in available:
        return last_mode
    selected = [frame for frame in frames if frame.selected]
    has_nuclei = any(frame.has_nucleus_segments() for frame in selected)
    has_whole_cells = any(frame_has_whole_cell_masks(frame) for frame in selected)
    if has_nuclei and not has_whole_cells:
        guess = NUCLEUS_ONLY
    elif has_whole_cells and not has_nuclei:
        guess = WHOLE_CELL_ONLY
    else:
        guess = BOTH
    return guess if guess in available else available[0]
