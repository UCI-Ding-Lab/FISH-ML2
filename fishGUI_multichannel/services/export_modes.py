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
    Return the export modes that can work for the selected frames and their stored masks.
    """
    if all_selected_frames_are_dapi_only(frames):
        return [NUCLEUS_ONLY]
    selected = [frame for frame in frames if frame.selected]
    has_nuclei = any(frame.has_nucleus_segments() for frame in selected)
    has_whole_cells = any(frame_has_whole_cell_masks(frame) for frame in selected)
    has_pairs = any(frame.has_nucleus_segments() and frame_has_whole_cell_masks(frame) for frame in selected)

    modes = []
    if has_nuclei:
        modes.append(NUCLEUS_ONLY)
    if has_whole_cells:
        modes.append(WHOLE_CELL_ONLY)
    if has_pairs:
        modes.append(BOTH)
    return modes or list(EXPORT_MODE_LABELS)


def export_mode_note(frames: list) -> str | None:
    """
    Explain why some export modes are greyed out for the selected frames, or None when all are available.
    """
    available = available_export_modes(frames)
    if len(available) == len(EXPORT_MODE_LABELS):
        return None
    if all_selected_frames_are_dapi_only(frames):
        return "Whole-cell modes need cytoplasm images.\nOnly DAPI images are loaded."
    reasons = []
    if NUCLEUS_ONLY not in available:
        reasons.append("No selected frame has DAPI nucleus masks yet.")
    if WHOLE_CELL_ONLY not in available:
        reasons.append("No selected frame has whole-cell masks yet.")
    if not reasons:
        reasons.append("Paired export needs a frame with both\nnucleus and whole-cell masks.")
    return "\n".join(reasons)


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
