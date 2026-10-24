import pickle
from tkinter import filedialog, messagebox
from ..gui.abstract import abstract
from ..gui.canvas.box import box
from ..gui.canvas.segment import segment
from .bundle_data import bundle
from .session_manager import SessionManager
from ..utils.sample_channels import channels_from_paths

class SessionSaveLoad:
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
