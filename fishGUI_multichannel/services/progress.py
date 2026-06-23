import pickle, threading, concurrent.futures, time
from tkinter import filedialog, messagebox
import logging
from ..gui.abstract import abstract
from ..gui.canvas.box import box
from ..gui.canvas.segment import segment
from .bundle_data import bundle
from .matPacker import create
from .session_manager import SessionManager
import re
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
            logger.info("Save session cancelled by user.")
            return
        try: 
            logger.info(f"Saving session to {filename}") 
            list_of_bundled_data = SessionManager.grabPool() 
            logger.info(f"Collected {len(list_of_bundled_data)} bundles") 
            with open(filename, "wb") as file: pickle.dump(list_of_bundled_data, file) 
            logger.info("Session saved successfully") 
            messagebox.showinfo("Done", "Session saved as " + filename) 
        except Exception as error:
            logger.exception("Session save failed") 
            messagebox.showerror("Save Error", str(error))  
        
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
            
        def create_abstract_object(sample_id, nucleus_path, cyto_paths, bbox_list, seg_dict, nucleus_centers, gui):
            abstract_object = abstract(
                sample_id, 
                nucleus_path=nucleus_path,
                cyto_paths=cyto_paths,
                gallery_frame=gui.getTifSequence().gallery_frame,
                gui=gui
            )
            abstract_object.bbox = [box(b, gui) for b in bbox_list]
            abstract_object.nucleus_centers = nucleus_centers
            for channel, mask_list in seg_dict.items():
                segs = [segment(gui, m) for m in mask_list]
                abstract_object.set_segments(channel, segs)
            abstract_object.bbox_generated = (bool(bbox_list) or bool(nucleus_centers))
            abstract_object.segment_generated = abstract_object.has_all_channel_segments()
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
                sample_id, nucleus_path, cytoplasm_paths, bbox_list, seg_dict = single_bundle.extract_data_from_bundles() 
                nucleus_centers = getattr(single_bundle, "nucleus_centers", [])
                valid_paths = return_valid_paths(nucleus_path, cytoplasm_paths) 
                if valid_paths is None: # prevent loading frames and its data with at least one invalid path
                    continue
                abs_obj =create_abstract_object(sample_id, nucleus_path, cytoplasm_paths, bbox_list, seg_dict, nucleus_centers, gui)
                gui.getSeasoning().update_channel_menu(abs_obj.available_channels)     
                gui.getSeasoning().update_channel_selector_for_image(abs_obj)
            except Exception as error:
                messagebox.showwarning("Skipped one row", f"Reason:{error}")
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
        
        d = {"name":[],"image":[],"xy":[],"masks":[]}
        prep_start = time.perf_counter()
        
        # get directory path
        directory_name = SessionManager.getImportDirectory()
        if not directory_name:
            directory_name = str(pathlib.Path(f).parent) # fallback to directory where export is saved

        # TODO - O(n^2) -  think of ways to improve effiiency
        for abs in toSave:
            cyto_paths = abs.getCytoplasmPaths()
            for path in cyto_paths:
                stem = path.stem.lower()
                match = re.search(r"(647|488|555|594|514)", stem)
                channel = match.group(1) if match else None
            
                if not abs.selected or channel is None or not abs.has_segments(channel):
                    img = None
                    xy = []
                    masks = []
                else:
                    segs = abs.get_segments(channel)
                    img = abs.getImgNumpyRGBCyto(channel)
                    xy = [mask.xy for mask in segs]
                    masks = [mask.box for mask in segs]

                d["name"].append(path.name)
                d["image"].append(img)
                d["xy"].append(xy)
                d["masks"].append(masks) 
        prep_seconds = time.perf_counter() - prep_start

        write_start = time.perf_counter()
        create(d["name"], d["xy"], d["masks"], f, dirname=str(directory_name))
        write_seconds = time.perf_counter() - write_start
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
                        f"Total {total_seconds:.2f}s"
                    ),
                ),
            )
        except Exception:
            pass
