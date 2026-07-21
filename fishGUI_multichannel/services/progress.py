import pickle, threading, concurrent.futures, time
from tkinter import filedialog, messagebox
import logging
from ..gui.abstract import abstract
from ..gui.canvas.box import box
from ..gui.canvas.segment import segment
from .bundle_data import bundle
from .export_pairs import build_paired_export_data
from .matPacker import create
from .pairing import export_pairing_debug_pdf
from .session_manager import SessionManager
from ..utils.sample_channels import channels_from_paths
import pathlib

logger = logging.getLogger('fishcore')

class Progress:
    @staticmethod
    def save():
        """
        Save current session data including all selected frames, its boundary boxes and 
        segmentation masks if exist.
        """
        filename = filedialog.asksaveasfilename(defaultextension=".pkl", 
                                         filetypes=[("Pickle files", "*.pkl")],
                                         title="Save Session As")
        if not filename: 
            return
        list_of_bundled_data = SessionManager.grabPool() # grabPool() returns a list of bundled data (includes file paths, bbox and masks for all abstract objects)
        with open(filename, "wb") as file:
            pickle.dump(list_of_bundled_data, file)
        messagebox.showinfo("Done", "Session saved as " + filename)    
        
    def load(gui):
        """
        Load previous session data (all abstract objects saved previously) including all selected frames, 
        its boundary boxes and segmentation masks if exist. 
        """
        # --- Helper Functions ---
        def get_filename_to_load():
            return filedialog.askopenfilename(filetypes=[("Progress files", "*.pkl")])
        
        def read_data_from_file(filename):
            try:
                with open(filename, "rb") as file:
                    return pickle.load(file) # returns list of bundled data 
            except Exception as error:
                messagebox.showerror("Error", f"Could not read {filename}:\n{error}")
                return None
        
        def clear_previous_session():
            """
            - getPool() returns a list of abstract objects in current session
            - clear() empties this list and references pointing to each objects are removed as well, 
              deleting all objects in current session automatically
            """
            SessionManager.getPool().clear()
            
        def return_valid_paths(nucleus_path, cytoplasm_paths):
            if not nucleus_path.exists():
                messagebox.showwarning("Missing file", f"Nucleus image not found:\n{nucleus_path}")
                return None
        
            missing_cytoplasm_file = [str(path) for path in cytoplasm_paths if not path.exists()]
            if missing_cytoplasm_file:
                messagebox.showwarning("Missing file", "Cytoplasm image(s) not found:\n" + "\n".join(missing_cytoplasm_file))
                return None
            
            return nucleus_path, cytoplasm_paths
            
        def create_abstract_object(sample_id, nucleus_path, cyto_paths, bbox_list, seg_dict, nucleus_masks, selected_channel, gui):
            channels = channels_from_paths(nucleus_path, cyto_paths)
            abstract_object = abstract(
                sample_id, 
                nucleus_path=nucleus_path,
                channels=channels,
                gallery_frame=gui.getTifSequence().gallery_frame,
                gui=gui
            )
            abstract_object.bbox = [box(b, gui) for b in bbox_list]
            abstract_object.nucleus_centers = abstract_object._compute_nucleus_centers_from_boxes(bbox_list)
            abstract_object.set_nucleus_segments([segment(gui, m) for m in nucleus_masks])
            for channel, mask_list in seg_dict.items():
                segs = [segment(gui, m) for m in mask_list]
                abstract_object.set_segments(channel, segs)
            if selected_channel in ["DAPI"] + abstract_object.available_channels:
                abstract_object.selected_channel = selected_channel
            return abstract_object

        # --- Main Logic ---
        loaded_filename = get_filename_to_load()
        if not loaded_filename: return
        session_data = read_data_from_file(loaded_filename)
        if session_data is None: return
        clear_previous_session()
        for item in session_data:
            try:
                single_bundle : bundle = item
                (
                    sample_id,
                    nucleus_path,
                    cytoplasm_paths,
                    bbox_list,
                    seg_dict,
                    nucleus_masks,
                    selected_channel,
                ) = single_bundle.extract_data_from_bundles() 
                valid_paths = return_valid_paths(nucleus_path, cytoplasm_paths) 
                if valid_paths is None: # prevent loading frames and its data with at least one invalid path
                    continue
                abs_obj = create_abstract_object(
                    sample_id,
                    nucleus_path,
                    cytoplasm_paths,
                    bbox_list,
                    seg_dict,
                    nucleus_masks,
                    selected_channel,
                    gui,
                )
                gui.getSeasoning().update_channel_menu(abs_obj.available_channels)     
                gui.getSeasoning().update_channel_selector_for_image(abs_obj)
            except Exception as error:
                messagebox.showwarning("Skipped one row", f"Reason:{error}")
        gui.setWorkflowMode("neutral")
        gui.getFuncButton().refresh_toolbar()
        SessionManager.sendFirst()

    @staticmethod
    def export(gui):
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
            for channel, path in cyto_channels_and_paths.items():
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
