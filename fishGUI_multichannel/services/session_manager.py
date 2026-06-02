import threading
import logging
import os
import csv
import pathlib
import time
from concurrent.futures import ThreadPoolExecutor
import pickle, threading, concurrent.futures, time

from ..services.bundle_data import bundle
from ..services.apply_channel_mask import apply_channel_mask_to_frames
from ..gui.abstract import abstract


logger = logging.getLogger('fishcore')


class SessionManager:
    __pool = []
    __buffer = None
    __importPath = None
    __segmentation_timing_rows = []
    __segmentation_timing_lock = threading.Lock()


    """
    Responsible for handling operations that affect the entire session
    or pool of abstract objects.
    """
    # --- Pool Management ---
    @classmethod
    def addToPool(cls, abstract_object):
        """
        Called when a new frame is loaded. 
        Adds this new abstract object to the current pool.
        """
        cls.__pool.append(abstract_object)

    @classmethod
    def getPool(cls):
        """
        Returns the list of all abstract objects currently managed in the session.
        """
        return cls.__pool

    @classmethod
    def setBuffer(cls, abstract_object: abstract):
        """
        Set one frame (abstract object) to focus
        """
        cls.__buffer = abstract_object

    @classmethod
    def getBuffer(cls):
        """
        Get focused frame        
        """
        return cls.__buffer

    # --- Selection/Focus Management ---
    @classmethod
    def selectAll(cls):
        """
        Marks all objects in the pool as selected.
        Used when the user turns the "select" mode on.
        """
        for abstract_object in cls.getPool():
            abstract_object.selected = True

    @classmethod
    def removeUnselected(cls):
        """
        Removes unselected frame from pool
        Resets the thumbnail for all objects and deletes the thumbnail
        for unselected ones. Then refocuses.
        """
        new_pool = []
        for abstract_object in list(cls.getPool()):
            if not isinstance(abstract_object, abstract):
                logger.debug(f"Object {abstract_object} is not an instance of abstract. Skipping.")
                continue
            if abstract_object.selected:
                abstract_object.thumbnail = "default"
                new_pool.append(abstract_object)
            else:
                try:
                    del abstract_object.thumbnail  # hides from UI
                except Exception as e:
                    logger.debug(f"Failed to delete thumbnail for {getattr(abstract_object,'sample_id','?')}: {e}")
        cls.__pool = new_pool
        cls.__buffer = None
        cls.sendFirst()

    @classmethod
    def sendFirst(cls):
        """
        Focuses the first selected object in the pool
        """
        for abstract_object in cls.getPool():
            if not isinstance(abstract_object, abstract):
                logger.debug(f"Object {abstract_object} is not an instance of abstract. Skipping.")
                return
            if abstract_object.selected:
                abstract_object.on_click(None)
                return
            
    @classmethod
    def sendFocused(cls):
        """
        Focuses the currently buffered object, or the first selected one
        if none is buffered. 
        """
        current = cls.getBuffer()
        if not isinstance(current, abstract):
            logger.debug(f"Object {current} is not an instance of abstract. Skipping.")
            return
        if current: current.on_click(None)
        else: cls.sendFirst()

    @classmethod
    def remove_segmentation_selection(cls):
        """
        Deselects all frames for segmentation in the pool.
        Ensures a clean state for new operations
        """
        for abstract_object in cls.getPool():
            if not isinstance(abstract_object, abstract):
                logger.debug(f"Object {abstract_object} is not an instance of abstract. Skipping.")
                continue 
            abstract_object.selected_for_segmentation = False  

    # --- Save/Segment/Batch Operations ---
    @classmethod
    def setImportDirectory(cls, folder):
        cls.__importPath = folder
    
    @classmethod
    def getImportDirectory(cls):
        return cls.__importPath

    @classmethod
    def _get_inference_worker_limit(cls, gui, total_jobs: int) -> int:
        backend = gui.getBackEnd()
        if getattr(backend, "device", "cpu") == "cuda":
            logger.info("GPU detected; limiting inference concurrency to 1 worker.")
            return 1
        return max(1, min(os.cpu_count() or 1, total_jobs))

    @classmethod
    def generate_bboxes(cls, gui):
        abstracts = cls.getPool()
        if not abstracts:
            return

        def job():
            max_workers = cls._get_inference_worker_limit(gui, len(abstracts))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for abs_obj in abstracts:
                    executor.submit(cls._generate_one_bbox, gui, abs_obj)

        threading.Thread(target=job, daemon=True).start()

    @classmethod
    def _generate_one_bbox(cls, gui, abs_obj):
        start_time = time.time()
        _ = abs_obj.bbox
        cls._refresh_if_loaded(gui, abs_obj)
        elapsed = time.time() - start_time
        logger.info("Computed nucleus centers for sample %s in %.4f seconds", abs_obj.sample_id, elapsed,)

    @classmethod
    def _refresh_if_loaded(cls, gui, abs_obj):
        loaded = gui.getStove().getLoaded()
        if loaded is not abs_obj:
            return
        gui.getRoot().after(0, lambda a=abs_obj: gui.getStove().cook(a))

    @classmethod
    def saveBboxChanges(cls):
        """
        Ensures GUI is now in a view-only mode. 
        Called when:
        - The user exits BBOX mode 
        - The user clicks on "Save" and Progress.save is called

        Note for Shizuka:
        Checkout ADDBOX_CALL in tools_panel.py
        Checkout abstract.py def bbox and its setter
        Checkout box.py and anchor.py
        1st line: this simply hides the overlay. the new bbox is saved in self.__bbox in abstract.py
        """
        cls.getBuffer().drawBbox = False 
        cls.sendFocused()

    @classmethod
    def saveSegChanges(cls):
        """
        Ensures GUI is now in a view-only mode. 
        Called when:
        - The user exits SEGMENT mode 
        - The user clicks on "Save" and Progress.save is called
        """
        cls.getBuffer().drawSegmentation = False
        cls.sendFocused()

    @classmethod
    def grabPool(cls) -> list['bundle']:
        """
        Overview: 
            Collects all selected frames and pacakges their data using the bundle class in services/bundle_data.
            Iterates over all abstract objects in the pool, and for each selected frame,
            creates a bundle object containing nucleus path, cytoplasm paths, revised bounding boxes,
            and revised segmentation masks. This is useful for saving session state and loading data.

        Returns:
            list[bundle]: A list of bundle objects, one for each selected frame.
        """
        result = []
        for abstract_object in cls.getPool():
            if not isinstance(abstract_object, abstract):
                logger.debug(f"Object {abstract_object} is not an instance of abstract. Skipping.")
                continue 
            if abstract_object.selected:
                seg_dict = {}
                for ch in abstract_object.SEGMENT_CHANNELS:
                    seg_dict[ch] = [s._segment__data.T for s in abstract_object.get_segments(ch)]
                bundled_info_for_save = bundle(
                    abstract_object.sample_id,
                    nucleus_path=abstract_object.getNucleusPath(),
                    cyto_paths=list(abstract_object.getCytoplasmPaths()),
                    bbox=abstract_object.boundingBoxRevised,
                    segment=seg_dict
                )
                result.append(bundled_info_for_save)
        return result

    @classmethod
    def get_all_available_channels(cls):
        """
        Returns a sorted list of all unique channels present in the current pool.
        """
        channels = set()
        for abs_obj in cls.getPool():
            # No hasattr needed, all abstract objects have available_channels
            channels.update(abs_obj.available_channels)
        return sorted(channels)
    
    @classmethod
    def apply_channel_mask_to_frames(cls, source_channel, selected_frames, target_channels, on_done=None):
        apply_channel_mask_to_frames(cls, source_channel, selected_frames, target_channels, on_done=on_done)


    @classmethod
    def segment_selected(cls, gui):
        """
        Runs segmentation on all frames that the user has marked as "selected for segmentation"
        """
        with cls.__segmentation_timing_lock:
            cls.__segmentation_timing_rows = []

        selected_frames = cls._get_selected_frames()
        ready, not_ready = cls._split_by_bbox_generated(selected_frames)
        if not_ready:
            cls._show_bbox_not_ready_popup(gui, not_ready)
        if not ready:
            return

        gui.popBox("i", "Segmentation", f"Started segmentation for {len(selected_frames)} images.")

        def monitor_threads():
            max_workers = cls._get_inference_worker_limit(gui, len(selected_frames))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(cls._segment_each, abs_obj, gui)
                    for abs_obj in selected_frames
                ]
                for future in futures:
                    future.result()
            cls._export_segmentation_timing_csv()
            gui.getFuncButton().toggle["SEGMENTATION_SELECTION"].set(0)

        threading.Thread(target=monitor_threads, daemon=True).start()


    @classmethod
    def _get_selected_frames(cls):
        """
        Returns frames that are selected for segmentation
        """
        selected_frames = [
            abstract_object for abstract_object in cls.getPool()
            if isinstance(abstract_object, abstract) and abstract_object.selected_for_segmentation
        ]
        logger.debug(
            f"Segmenting {len(selected_frames)} images: "
            f"{[str(abstract_object.getNucleusPath().name) for abstract_object in selected_frames]}"
        )
        return selected_frames

    @classmethod
    def _split_by_bbox_generated(cls, frames):
        ready = []
        not_ready = []
        for obj in frames:
            if obj.bbox_generated:
                ready.append(obj)
            else:
                not_ready.append(obj)
        return ready, not_ready
    
    @classmethod
    def _ui_show_segmented(cls, a, gui):
        a.thumbnail = "segmented" # blue and orange
        a.selected_for_segmentation = False
        if a is cls.getBuffer() and gui.getFuncButton().segButtonPressed():
            a.drawSegmentation = True


    @classmethod
    def _segment_each(cls, abs_obj: abstract, gui):
        thread_name = threading.current_thread().name
        logger.debug(f"Thread {thread_name} STARTED for sample {abs_obj.sample_id}")
        start = time.perf_counter()

        original_channel = abs_obj.selected_channel
        channels_to_segment = [ch for ch in abs_obj.available_channels if ch in abs_obj.SEGMENT_CHANNELS]
        for ch in channels_to_segment:
            abs_obj.segment_channel(ch)
        abs_obj.selected_channel = original_channel
        abs_obj.segment_generated = abs_obj.has_any_segments()

        elapsed = time.perf_counter() - start
        num_masks = len(abs_obj.get_segments(abs_obj.selected_channel))
        frame_number = f"s{str(abs_obj.sample_id).zfill(3)}"
        with cls.__segmentation_timing_lock:
            cls.__segmentation_timing_rows.append({
                "frame_number": frame_number,
                "segmentation_seconds": round(elapsed, 3),
                "num_masks_predicted": num_masks,
            })

        gui.getRoot().after(0, lambda a=abs_obj: cls._ui_show_segmented(a, gui))
        logger.debug(f"Thread {thread_name} FINISHED for sample {abs_obj.sample_id} in {elapsed:.2f}s")



    @classmethod
    def _export_segmentation_timing_csv(cls):
        import_dir = cls.getImportDirectory()
        if import_dir is None:
            logger.warning("No import directory set; skipping segmentation timing export.")
            return

        if not cls.__segmentation_timing_rows:
            logger.warning("No segmentation timing rows to export.")
            return

        import_dir = pathlib.Path(import_dir)
        out_path = import_dir / f"{import_dir.name}_segmentation_timing.csv"

        rows = sorted(cls.__segmentation_timing_rows, key=lambda r: r["frame_number"])

        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["frame_number", "segmentation_seconds", "num_masks_predicted"],
            )
            writer.writeheader()
            writer.writerows(rows)

        logger.info("Saved segmentation timing table to %s", out_path)
