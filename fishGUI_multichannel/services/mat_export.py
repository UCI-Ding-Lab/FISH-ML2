import logging
import pathlib
import time
from tkinter import filedialog, messagebox

from .export_cell_data import build_paired_export_data
from .matPacker import create
from .pairing import export_pairing_debug_pdf
from .session_manager import SessionManager

logger = logging.getLogger('fishcore')


def export_session_to_mat(gui):
    """Export the selected frames as a MATLAB .mat file for DoFISH."""
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

    for abs in toSave:
        cyto_channels_and_paths = abs.getCytoplasmChannelsAndPaths()
        channel_items = list(cyto_channels_and_paths.items())
        if not channel_items:
            continue
        channel, path = channel_items[0]
        if not abs.selected or not abs.has_segments(channel):
            img = None
            xy = []
            masks = []
            nucleus_masks = []
        else:
            img = abs.getImgNumpyRGBForChannel(channel)
            xy, masks, nucleus_masks = build_paired_export_data(abs, channel)

        d["name"].append(path.name)
        d["image"].append(img)
        d["xy"].append(xy)
        d["masks"].append(masks)
        d["nucleus_masks"].append(nucleus_masks)
    prep_seconds = time.perf_counter() - prep_start

    write_start = time.perf_counter()
    create(d["name"], d["xy"], d["masks"], d["nucleus_masks"], f, dirname=str(directory_name))
    write_seconds = time.perf_counter() - write_start
    debug_pdf_path = None
    if should_export_pairing_debug_pdf(gui):
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


def should_export_pairing_debug_pdf(gui) -> bool:
    """Return whether the current GUI wants the optional pairing debug PDF."""
    try:
        return gui.shouldExportPairingDebugPdf()
    except AttributeError:
        return False
