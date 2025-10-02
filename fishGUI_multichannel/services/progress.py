import pickle, threading, concurrent.futures, time
from tkinter import filedialog, messagebox
from ..gui.abstract import abstract
from ..gui.canvas.box import box
from ..gui.canvas.segment import segment
from .bundle_data import bundle
from .matPacker import create
from .session_manager import SessionManager

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
                messagebox.showwarning("Missing file", "Nucleus image not found:\n{nucleus_path}")
                return None
        
            missing_cytoplasm_file = [str(path) for path in cytoplasm_paths if not path.exists()]
            if missing_cytoplasm_file:
                messagebox.showwarning("Missing file", "Cytoplasm image(s) not found:\n" + "\n".join(missing_cytoplasm_file))
                return None
            
            return nucleus_path, cytoplasm_paths
            
        def create_abstract_object(sample_id, nucleus_path, cyto_paths, bbox_list, seg_dict, gui):
            abstract_object = abstract(
                sample_id, 
                nucleus_path=nucleus_path,
                cyto_paths=cyto_paths,
                gallery_frame=gui.getTifSequence().gallery_frame,
                gui=gui
            )
            abstract_object.bbox = [box(b, gui) for b in bbox_list]
            seg_647 = [segment(gui, m) for m in seg_dict.get("647", [])]
            seg_488 = [segment(gui, m) for m in seg_dict.get("488", [])]
            abstract_object._abstract__seg_647 = seg_647
            abstract_object._abstract__seg_488 = seg_488
            # Set current channel mask to the selected channel TODO - clean with abstractpy
            if getattr(abstract_object, "selected_channel", "647") == "647":
                abstract_object._abstract__current_channel_mask = seg_647
            else:
                abstract_object._abstract__current_channel_mask = seg_488
            if seg_647 or seg_488:
                abstract_object.segment_generated = True
            return abstract_object

        # --- Main Logic ---
        loaded_filename = get_filename_to_load()
        if not loaded_filename: return
        session_data = read_data_from_file(loaded_filename)
        if session_data is None: return
        clear_previous_session()
        for item in session_data:
            print(type(item))
            try:
                single_bundle : bundle = item
                sample_id, nucleus_path, cytoplasm_paths, bbox_list, seg_dict = single_bundle.extract_data_from_bundles() 
                valid_paths = return_valid_paths(nucleus_path, cytoplasm_paths) 
                if valid_paths is None: # prevent loading frames and its data with at least one invalid path
                    continue
                abs_obj =create_abstract_object(sample_id, nucleus_path, cytoplasm_paths, bbox_list, seg_dict, gui)
                gui.getSeasoning().update_channel_menu(abs_obj.available_channels)     
                gui.getSeasoning().update_channel_selector_for_image(abs_obj)
            except Exception as error:
                messagebox.showwarning("Skipped one row", f"Reason:{error}")
        SessionManager.sendFirst()

    # @staticmethod
    # def generateBbox(gui, list_of_abstract_objects: list[abstract]):
    #     """
    #     Generates bounding boxes using multithreading
    #     Called in gui/buttons.py, IMPORT_call method
    #     This ensures that boundary boxes are generate once images are imported
    #     """
    #     # --- Helper functions ---
    #     def generate_bbox_for_object(single_abstract_object: abstract):
    #         t0 = time.perf_counter()
    #         start_time = time.time()
    #         _ = single_abstract_object.bbox
    #         end_time = time.time()
    #         print(f"Generated bbox for {single_abstract_object.getNucleusPath()} in {end_time - start_time:.4f} seconds")

    #     def generate_bboxes():
    #         max_workers = min(3, len(list_of_abstract_objects))
    #         with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
    #             executor.map(generate_bbox_for_object, list_of_abstract_objects)

    #     # --- Main Logic ---
    #     t1 = time.perf_counter()
    #     print(f"[BBOX] ALL {len(list_of_abstract_objects)} images finished in {t1 - t0:.2f}s total")
    #     threading.Thread(target=generate_bboxes, daemon=True).start() # Start the thread of generating bboxes

    import time, sys, threading, concurrent.futures

    @staticmethod
    def generateBbox(gui, list_of_abstract_objects: list['abstract']):
        """
        Generates bounding boxes using multithreading.
        Called in gui/buttons.py, IMPORT_call method.
        """

        def generate_bbox_for_object(single_abstract_object: 'abstract'):
            t_start = time.perf_counter()
            try:
                print(f"[BBOX] START {single_abstract_object.getNucleusPath()}", flush=True)
                _ = single_abstract_object.bbox
                print(f"[BBOX] DONE  {single_abstract_object.getNucleusPath()} "
                    f"in {time.perf_counter() - t_start:.2f}s", flush=True)
            except Exception as e:
                print(f"[BBOX] ERROR {single_abstract_object.getNucleusPath()} -> {e}", flush=True)

        def generate_bboxes():
            t0 = time.perf_counter()
            max_workers = min(3, len(list_of_abstract_objects))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(executor.map(generate_bbox_for_object, list_of_abstract_objects))
            print(f"[BBOX] ALL {len(list_of_abstract_objects)} images finished "
                f"in {time.perf_counter() - t0:.2f}s total", flush=True)

        threading.Thread(target=generate_bboxes, daemon=False).start()
