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
from .export_modes import BOTH, NUCLEUS_ONLY, WHOLE_CELL_ONLY
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

    d = {"name":[],"image":[],"xy":[],"masks":[],"nucleus_masks":[]}
    prep_start = time.perf_counter()

    # get directory path
    directory_name = SessionManager.getImportDirectory()
    if not directory_name:
        directory_name = str(pathlib.Path(f).parent) # fallback to directory where export is saved

    # DAPI-only frames are exported only when every selected frame is DAPI-only, so DoFISH
    # never looks for cytoplasm channel images that do not exist
    include_dapi_only_frames = export_mode == NUCLEUS_ONLY and all_selected_frames_are_dapi_only(toSave)

    for abs in toSave:
        first_channel = first_cytoplasm_channel_and_path(abs)
        if first_channel is None:
            if not include_dapi_only_frames:
                continue
            channel, path = None, abs.getNucleusPath()
        else:
            channel, path = first_channel
        if not abs.selected or not frame_has_masks_for_mode(abs, channel, export_mode):
            img = None
            xy = []
            masks = []
            nucleus_masks = []
        else:
            img = abs.getImgNumpyRGBForChannel(channel)
            xy, masks, nucleus_masks = build_frame_cells(abs, channel, export_mode)

        d["name"].append(path.name)
        d["image"].append(img)
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

    try:
        gui.getRoot().after(
            0,
            lambda: messagebox.showinfo(
                "Export Complete",
                (
                    f"Prepared {len(d['name'])} entries in {prep_seconds:.2f}s\n"
                    f"Wrote MAT in {write_seconds:.2f}s\n"
                    f"Pairing PDF: {debug_pdf_path.name if debug_pdf_path else 'not written'}\n"
                    f"Total {total_seconds:.2f}s"
                ),
            ),
        )
    except Exception:
        pass


def frame_has_masks_for_mode(frame, channel: str, export_mode: str) -> bool:
    """Return True when one frame has the masks the chosen export mode needs."""
    if export_mode == NUCLEUS_ONLY:
        return frame.has_nucleus_segments()
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
