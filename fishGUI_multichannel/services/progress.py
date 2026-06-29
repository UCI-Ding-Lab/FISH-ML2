import pickle, threading, concurrent.futures, time
from tkinter import filedialog, messagebox
from ..gui.abstract import abstract
from ..gui.canvas.box import box
from ..gui.canvas.segment import segment
from .bundle_data import bundle
from .matPacker import create
from .session_manager import SessionManager
from ..utils.sample_channels import (
    channels_from_paths,
    get_cytoplasm_paths_and_names,
)
import pathlib

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
            
        def create_abstract_object(
            sample_id,
            nucleus_path,
            cyto_paths,
            bbox_list,
            seg_dict,
            nucleus_centers,
            gui,
        ):
            channels = channels_from_paths(nucleus_path, cyto_paths)
            if "DAPI" not in channels:
                messagebox.showwarning(
                    "Missing DAPI",
                    f"Could not resolve a DAPI path for sample {sample_id}; skipping.",
                )
                return None

            cyto_paths, cyto_channels = get_cytoplasm_paths_and_names(channels)
            abstract_object = abstract(
                sample_id,
                nucleus_path=nucleus_path,
                cyto_paths=cyto_paths,
                cyto_channels=cyto_channels,
                channels=channels,
                gallery_frame=gui.getTifSequence().gallery_frame,
                gui=gui,
            )
            if nucleus_centers:
                abstract_object.nucleus_centers = [
                    (float(x), float(y)) for x, y in nucleus_centers
                ]
            abstract_object.bbox = [box(b, gui) for b in bbox_list]
            if abstract_object.getNucleusCenters() or bbox_list:
                abstract_object.bbox_generated = True
            elif not abstract_object.bbox_generated:
                _ = abstract_object.bbox
            for ch, mask_list in seg_dict.items():
                seg_objs = [segment(gui, m) for m in mask_list]
                abstract_object._set_seg_obj_for_channel(ch, seg_objs)
            abstract_object.segment_generated = any(seg_dict.values())
            if abstract_object.selected_channel:
                abstract_object.seg = abstract_object._get_seg_obj_for_channel(
                    abstract_object.selected_channel
                )
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
                    nucleus_centers,
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
                    nucleus_centers,
                    gui,
                )
                if abs_obj is None:
                    continue
                gui.getSeasoning().update_channel_menu(abs_obj.available_channels)     
                gui.getSeasoning().update_channel_selector_for_image(abs_obj)
            except Exception as error:
                messagebox.showwarning("Skipped one row", f"Reason:{error}")
        SessionManager.sendFirst()

    @staticmethod
    def export(gui):
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
        
        # get directory path
        directory_name = SessionManager.getImportDirectory()
        if not directory_name:
            directory_name = str(pathlib.Path(f).parent) # fallback to directory where export is saved

        # TODO - O(n^2) -  think of ways to improve effiiency
        for abs in toSave:
            cyto_chnls_and_paths = abs.getCytoplasmChannelsAndPaths()
            for channel, path in cyto_chnls_and_paths.items():
                seg_objs = abs._get_seg_obj_for_channel(channel)
                if not abs.selected or not seg_objs:
                    img = None
                    xy = []
                    masks = []
                else:
                    img = abs.getImgNumpyRGBCyto(channel)
                    xy = [mask.xy for mask in seg_objs]
                    masks = [mask.box for mask in seg_objs]

                d["name"].append(path.name)
                d["image"].append(img)
                d["xy"].append(xy)
                d["masks"].append(masks) 
        create(d["name"], d["xy"], d["masks"], f, dirname=str(directory_name))
