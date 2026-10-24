import logging
import pathlib
import time
from tkinter import filedialog, messagebox

from .export_cell_data import (
    all_selected_frames_are_dapi_only,
    build_nucleus_only_export_data,
    build_paired_export_data,
    build_whole_cell_only_export_data,
    first_cytoplasm_channel_and_path,
)
from .export_modes import BOTH, EXPORT_MODE_LABELS, NUCLEUS_ONLY, WHOLE_CELL_ONLY
from .mat_file_writer import write_tracked_mat_file
from .pairing import export_pairing_debug_pdf
from .session_manager import SessionManager

logger = logging.getLogger('fishcore')


def export_session_to_mat(gui, export_mode: str = BOTH):
    """Export the selected frames as a MATLAB .mat file for DoFISH, using one export mode."""
    total_start = time.perf_counter()
    f = filedialog.asksaveasfilename(defaultextension=".mat", 
                                     filetypes=[("Matlab files", "*.mat")],
                                     title="Export Results As")
    if not f: 
        return

    # Check if any frames have segmentation data
    toSave = [i for i in SessionManager.getPool()]
    if not toSave:
        messagebox.showwarning("No Data", "No frames with segmentation data found")
        return

    d = {"name":[],"xy":[],"masks":[],"nucleus_masks":[]}
    prep_start = time.perf_counter()

    # get directory path
    directory_name = SessionManager.getImportDirectory()
    if not directory_name:
        directory_name = str(pathlib.Path(f).parent) # fallback to directory where export is saved

    # DAPI-only frames are exported only when every selected frame is DAPI-only, so DoFISH
    # never looks for cytoplasm channel images that do not exist
    include_dapi_only_frames = export_mode == NUCLEUS_ONLY and all_selected_frames_are_dapi_only(toSave)
    empty_frame_names = []
    skipped_dapi_only_names = []
    left_out = {"cells": 0, "nuclei": 0}

    for abs in toSave:
        first_channel = first_cytoplasm_channel_and_path(abs)
        if first_channel is None:
            if not include_dapi_only_frames:
                if abs.selected:
                    skipped_dapi_only_names.append(abs.getNucleusPath().name)
                continue
            channel, path = None, abs.getNucleusPath()
        else:
            channel, path = first_channel
        if abs.selected and export_mode == BOTH and channel is not None and frame_has_masks_for_mode(abs, channel, export_mode):
            abs.update_pairings_for_channel(channel)
            add_left_out_counts(left_out, abs.get_pairings(channel))

        if not abs.selected or not frame_has_masks_for_mode(abs, channel, export_mode):
            xy = []
            masks = []
            nucleus_masks = []
        else:
            xy, masks, nucleus_masks = build_frame_cells(abs, channel, export_mode)
        if abs.selected and not xy:
            empty_frame_names.append(path.name)

        d["name"].append(path.name)
        d["xy"].append(xy)
        d["masks"].append(masks)
        d["nucleus_masks"].append(nucleus_masks)
    prep_seconds = time.perf_counter() - prep_start

    write_start = time.perf_counter()
    nucleus_masks_to_write = d["nucleus_masks"] if export_mode == BOTH else None
    write_tracked_mat_file(d["name"], d["xy"], d["masks"], nucleus_masks_to_write, f, dirname=str(directory_name))
    write_seconds = time.perf_counter() - write_start
    debug_pdf_path = None
    if export_mode == BOTH and should_export_pairing_debug_pdf(gui):
        debug_pdf_path = export_pairing_debug_pdf([frame for frame in toSave if frame.selected], pathlib.Path(directory_name))
    total_seconds = time.perf_counter() - total_start

    logger.info(
        "Export timing for %s: prepared %d entries in %.2fs, wrote MAT in %.2fs, total %.2fs",
        pathlib.Path(f).name,
        len(d["name"]),
        prep_seconds,
        write_seconds,
        total_seconds,
    )

    summary = (
        f"Prepared {len(d['name'])} entries in {prep_seconds:.2f}s\n"
        f"Wrote MAT in {write_seconds:.2f}s\n"
        f"Pairing PDF: {debug_pdf_path.name if debug_pdf_path else 'not written'}\n"
        f"Total {total_seconds:.2f}s"
    )
    if export_mode == BOTH:
        summary += "\n\n" + describe_left_out(left_out, debug_pdf_path is not None)
    warning = build_export_warning(empty_frame_names, skipped_dapi_only_names, export_mode)
    show_export_complete(gui, summary, warning)


def add_left_out_counts(left_out: dict, pairing: dict) -> None:
    """Add one frame's whole-cell and nucleus masks that found no partner to the running totals."""
    left_out["cells"] += len(pairing["unmatched_cytoplasms"])
    left_out["nuclei"] += len(pairing["unmatched_nuclei"])


def describe_left_out(left_out: dict, debug_pdf_written: bool) -> str:
    """Say how many masks paired export left out, and how to see which ones."""
    cells, nuclei = left_out["cells"], left_out["nuclei"]
    text = (
        f"Left out (no partner): {cells} whole-cell mask{'' if cells == 1 else 's'} "
        f"and {nuclei} nucleus mask{'' if nuclei == 1 else 's'}"
    )
    if cells + nuclei == 0:
        return text
    if debug_pdf_written:
        return text + "\nThey are outlined in red in the pairing PDF."
    return text + "\nStart FishGUI with --export-pairing-debug-pdf to see which ones."


def build_export_warning(empty_frame_names: list, skipped_dapi_only_names: list, export_mode: str) -> str | None:
    """Describe selected frames that ended up with no cells, or None when every selected frame has cells."""
    parts = []
    if empty_frame_names:
        parts.append(
            f"{len(empty_frame_names)} selected frame(s) were exported with 0 cells "
            f"(no masks for {EXPORT_MODE_LABELS[export_mode]}):\n"
            + format_frame_names(empty_frame_names)
        )
    if skipped_dapi_only_names:
        if export_mode == NUCLEUS_ONLY:
            reason = "other selected frames have cytoplasm images"
        else:
            reason = f"{EXPORT_MODE_LABELS[export_mode]} needs cytoplasm images"
        parts.append(
            f"{len(skipped_dapi_only_names)} DAPI-only frame(s) were left out because {reason}:\n"
            + format_frame_names(skipped_dapi_only_names)
        )
    return "\n\n".join(parts) if parts else None


def format_frame_names(frame_names: list, limit: int = 10) -> str:
    """List frame names one per line, shortening long lists."""
    lines = [f"  {name}" for name in frame_names[:limit]]
    if len(frame_names) > limit:
        lines.append(f"  ... and {len(frame_names) - limit} more")
    return "\n".join(lines)


def show_export_complete(gui, summary: str, warning: str | None) -> None:
    """Show the export summary on the main Tk thread, as a warning when some frames have no cells."""
    def show():
        """Show one popup with the summary and any warning."""
        if warning:
            messagebox.showwarning("Export Complete With Warnings", f"{summary}\n\n{warning}")
        else:
            messagebox.showinfo("Export Complete", summary)

    try:
        gui.getRoot().after(0, show)
    except Exception:
        pass


def frame_has_masks_for_mode(frame, channel: str, export_mode: str) -> bool:
    """Return True when one frame has the masks the chosen export mode needs."""
    if export_mode == NUCLEUS_ONLY:
        return frame.has_nucleus_segments()
    if export_mode == BOTH:
        return frame.has_nucleus_segments() and frame.has_segments(channel)
    return frame.has_segments(channel)


def build_frame_cells(frame, channel: str, export_mode: str) -> tuple[list, list, list]:
    """Build one frame's cell positions, masks, and nucleus masks for the chosen export mode."""
    if export_mode == NUCLEUS_ONLY:
        xy, masks = build_nucleus_only_export_data(frame)
        return xy, masks, []
    if export_mode == WHOLE_CELL_ONLY:
        xy, masks = build_whole_cell_only_export_data(frame, channel)
        return xy, masks, []
    return build_paired_export_data(frame, channel)


def should_export_pairing_debug_pdf(gui) -> bool:
    """Return whether the current GUI wants the optional pairing debug PDF."""
    try:
        return gui.shouldExportPairingDebugPdf()
    except AttributeError:
        return False
