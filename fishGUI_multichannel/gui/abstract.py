import threading
import time
import pathlib
import numpy as np
import tifffile
import tkinter
from PIL import Image, ImageTk, ImageDraw
import logging
from .canvas.box import box
from .canvas.segment import segment
from ..services.segmentation import run_cytoplasm_segmentation, run_nucleus_segmentation
from ..services.pairing import build_pairing_result, clone_pairing_result, make_empty_pairing_result
from ..utils.image_preprocessing import (
    normalize_to_uint8,
    grayscale_to_rgb,
    preprocess_nucleus_stack,
    preprocess_cytoplasm_stack,
    preprocess_cytoplasm_channels,
)

logger = logging.getLogger('fishcore')

class abstract():
    """
    The abstract class represent one frame's state 

    This class handles:
    1) Initialization
    - Which paths to store for this frame
    - Loading and preprocessing nucleus and cytoplasm images
    - Tracking which cytoplasmic channels are available

    2) Maintaining various states of this frame
    - Which channel is currently selected
    - Managing selection state for filtering out bad frames
    - Managing selection state for segmentation batch selection
    - Computing and storing nucleus center coordinates
    - Keeping segmentation masks for each cytoplasmic channel
    - Providing the mask list for the selected channel

    3) Frame Specific UI Updates
    - Managing the thumbnail’s state in the gallery (blue, green, orange overlays)
    - Handling all frame-specific interactions with the main GUI
    """

    SEGMENT_CHANNELS = ("647", "488", "555", "594", "514")
    
    def __init__(
        self,
        sample_id, 
        nucleus_path: pathlib.Path,
        cyto_paths: list[pathlib.Path],
        gallery_frame,
        gui
    ):
        # --- DECLARE INSTANCE VARIABLES ---
        self.sample_id = sample_id 
        self.__nucleus_path = nucleus_path
        self.__cyto_paths = cyto_paths
        self.gui = gui

        # Thumbnail states
        self.__img_pil_thumbnail_bbox = None # image with bbox overlay - blue dot -- NOTE cellpose-sam version may not need bbox, but this overlay can be used to signifiy that nucleus center was computed
        self.__img_pil_thumbnail_select = None # image with selection overlay - green dot
        self.__img_pil_thumbnail_crossout = None  # image with crossout overlay - red X
        self.__img_pil_thumbnail_segmented = None # image with segmentation overlay - orange dot
        self.__img_pil_thumbnail_segmentation_selected = None   # image with selection and bbox overlay -- green and blue dot -- TODO : ensure that user cannot select a frame without bbox 
        self.__img_pil_thumbnail_selected_and_segmented = None # image that was selected and segmentation is complete - blue and orange dot

        self.__img_tk_thumbnail_bbox = None 
        self.__img_tk_thumbnail_select = None
        self.__img_tk_thumbnail_crossout = None
        self.__img_tk_thumbnail_segmented = None
        self.__img_tk_thumbnail_segmentation_selected = None  
        self.__img_tk_thumbnail_selected_and_segmented = None 

        self.__thumbnail_state: str = None # Current thumbnail state 

        # Selection states
        self.__selected: bool = True 
        self.__selected_for_segmentation: bool = False 
        self.__highlighted: str = None # focused frame;  used in on_click()
        self.nucleus_centers: list[tuple] = [] # TODO change to private variable and use getter to ensure consistency

        # Boundary boxes
        self.__bbox = [] # list of bbox generated for an abstract instance
        self.__bbox_generated: bool = False
        self.__drawBbox: bool = False
        
        # Segmentation masks
        self.__nucleus_segments = []
        self.__current_channel_mask = [] 
        self.__channel_segments = {ch: [] for ch in self.SEGMENT_CHANNELS}
        self.__channel_pairings = {ch: make_empty_pairing_result() for ch in self.SEGMENT_CHANNELS}
        self.__segment_generated: bool = False
        self.__drawSeg: bool = False
        self.__channel_rgb_cache = {}

        # --- MAIN INITIALIZATION LOGIC ---
        # Load images
        self.__img_np_nucleus = self._load_nucleus(nucleus_path) 
        self.__img_np_647, self.__img_np_488,  self.__img_np_555, self.__img_np_594, self.__img_np_514 = self._load_cytoplasms(cyto_paths)

        # Get available channels and set default channel
        self.available_channels = self._get_available_channels()
        self.__current_channel = self._initialize_default_channel(self.available_channels)
        if self.__current_channel is None:
            logger.warning(f"No available cytoplasm channels for sample {self.sample_id} at {nucleus_path}")

        # Build thumbnail gallery
        thumbnail_img = self._initialize_thumbnail_img()
        self.__img_np_rgb = grayscale_to_rgb(thumbnail_img) # NOTE Many display libraries, including Tkinter, PIL, and matplotlib, expect images to be in RGB format
        self.__img_pil_thumbnail, self.__img_tk_thumbnail = self._create_pil_and_tkinter_thumbnail(self.__img_np_rgb) # Convert image to display on tkinter thumbnail & main canvas
        self.__label = self._create_gallery_thumbnail(gallery_frame, self.__img_tk_thumbnail)
        self._setup_gallery_thumbnail_label_bindings(self.__label)

        from ..services.session_manager import SessionManager
        SessionManager.addToPool(self)

    # --- Helper for Initialization ---
    def _load_nucleus(self, nucleus_path: pathlib.Path) -> np.ndarray:
        """
        Loads nucleus image from imported path. If the image hasn't been
        z-projected, it will apply manual z-projection; else returns 
        imported image in grayscale. np.squeeze() removes any dimensions of size 1
        while normalize_to_unit8 scales the image array to 0 and 255. 

        Returns:
        - gray-scale image to ensure compatibility with groundingdino and SAM
        """
        nucleus_array = tifffile.imread(nucleus_path)
        if nucleus_array.ndim == 3 and nucleus_array.shape[0] > 1:
            return preprocess_nucleus_stack(nucleus_array)
        return normalize_to_uint8(np.squeeze(nucleus_array)) # already z-projected
    

    def _load_cytoplasms(self, cyto_paths: list[pathlib.Path]) -> tuple[np.ndarray, np.ndarray]:
        """
        Returns the preprocessed image (normalized grayscale) for both 647 and 488
        If either channel does not exist, it returns None

        Returns:
        - gray-scale image to ensure compatibility with groundingdino and SAM
        """
        channel_images = {}
        for cyto_path in cyto_paths:
            cyto_array = tifffile.imread(cyto_path)
            zprojected = (
                preprocess_cytoplasm_stack(cyto_array, top_n=8)
                if cyto_array.ndim == 3 and cyto_array.shape[0] > 1
                else np.squeeze(cyto_array)
            )
            stem = cyto_path.stem.lower()
            if "647" in stem:
                channel_images["647"] = zprojected
            elif "488" in stem:
                channel_images["488"] = zprojected
            elif "555" in stem:
                channel_images["555"] = zprojected
            elif "594" in stem:
                channel_images["594"] = zprojected
            elif "514" in stem:
                channel_images["514"] = zprojected
            else:
                logger.warning(f"Unrecognized cytoplasm channel in file {cyto_path.name}")

        processed = preprocess_cytoplasm_channels(channel_images)
        return (
            processed.get("647"),
            processed.get("488"),
            processed.get("555"),
            processed.get("594"),
            processed.get("514"),
        )
        
        
    def _get_available_channels(self) -> list[str]:
        channels = []
        if self.__img_np_647 is not None:
            channels.append("647")
        if self.__img_np_488 is not None:
            channels.append("488")
        if self.__img_np_555 is not None:
            channels.append("555")
        if self.__img_np_594 is not None:
            channels.append("594")
        if self.__img_np_514 is not None:
            channels.append("514")
        return channels


    def _initialize_default_channel(self, channels):
        return channels[0] if channels else None


    def _initialize_thumbnail_img(self):
        """
        Returns the image to use for the thumbnail
        """
        for ch in self.available_channels:
            if ch == "647" and self.__img_np_647 is not None:
                return self.__img_np_647
            elif ch == "488" and self.__img_np_488 is not None:
                return self.__img_np_488
            elif ch == "555" and self.__img_np_555 is not None:
                return self.__img_np_555
            elif ch == "594" and self.__img_np_594 is not None:
                return self.__img_np_594
            elif ch == "514" and self.__img_np_514 is not None:
                return self.__img_np_514
        return self.__img_np_nucleus


    def _create_pil_and_tkinter_thumbnail(self, img_np_rgb, size=(64, 64)):
        """
        # Convert numpy image to display on tkinter thumbnail & main canvas
        Returns (pil_image, tk_image)
        """
        pil = Image.fromarray(img_np_rgb).resize(size) # used for image processing, drawing or saving
        tk_img = ImageTk.PhotoImage(pil) # image that will be displayed on gui
        return pil, tk_img


    def _create_gallery_thumbnail(self, gallery_frame, tk_img, size=(64, 64)):
        """
        Creates and configures a Tkinter Label widget for the gallery thumbnail.
        Returns the label widget.
        """
        label = tkinter.Label(
            gallery_frame,
            image=tk_img,
            width=size[0], height=size[1],
            relief=tkinter.FLAT, borderwidth=0
        )
        label.pack(side=tkinter.LEFT, padx=2, pady=2)
        label.config(width=size[0], height=size[1])
        return label
       

    # --- Frame Selection States --- 
    @property
    def selected(self) -> bool:
        return self.__selected
    @selected.setter
    def selected(self, value: bool):
        """
        Manages the selection state of a frame. If the user determines that a frame 
        is unsuitable for downstream analysis (e.g. lacking clear cells), they can 
        exclude it from further processing.
        """
        if value:
            self.thumbnail = "selected" # NOTE self.thumbnail calls setter for thumbnail
            self.__selected = True
        else:
            self.thumbnail = "crossout"
            self.__selected = False

    @property
    def selected_for_segmentation(self):
        return self.__selected_for_segmentation
    @selected_for_segmentation.setter
    def selected_for_segmentation(self, value):
        """
        Manages the seleciton state of the frame to be segmented for all channels. 
        """
        self.__selected_for_segmentation = value
        self.update_thumbnail()


    # --- Selected Channel ---
    @property
    def selected_channel(self):
        return self.__current_channel
    @selected_channel.setter
    def selected_channel(self, new_channel):
        """
        Based on the newly selected channel, update the current mask
        and update the thumbnail 
        """
        if new_channel == self.__current_channel:
            return
        self.__current_channel = new_channel
        self.__current_channel_mask = self._get_mask_list_for_display_channel(new_channel)
        self.__img_np_rgb = self._get_rgb_for_display_channel(new_channel)
        self.update_thumbnail() # TODO should thumbnail be updated in thumbnaisl.py? 


    # --- Boundary Boxes / Nucleus Center Generation --- # TODO replace name with nucleus generation, remove unnecessary parts 
    @property
    def bbox(self):
        """
        Compute nucleus centers
        """
        if not self.bbox_generated: # NOTE new logic for cellpose-sam: if nucleus bbox is not generated
            nuc_boxes = self.gui.getBackEnd().AppIntDINOwrapper(self.__img_np_nucleus)
            centers = [
                ((x0 + x1) / 2, (y0 + y1) / 2)
                for x0, y0, x1, y1 in nuc_boxes
            ]
            self.nucleus_centers = centers
            if not self.has_nucleus_segments():
                self.segment_nucleus()
            # logger.info(f"Computed nucleus centers : {nuc_boxes}")
            self.bbox_generated = True # TODO change to nucleus_center_computed if bbox is unnecessary
        return self.__bbox
        

    # --- Segmentation Logic ---
    @property
    def segment(self) -> list[segment]:
        """
        Run Cellpose-SAM for all available cytoplasmic channels,
        store each channel's masks, and return the active channel mask

        Flow: 
        segment_call (buttons.py) -> segment_selected (session_manager.py) 
        -> segment_each (session_manager.py) -> segment (abstract.py) 
        -> run_cellpose_segmentation (segmentation.py)
        """
        return self.segment_channel(self.selected_channel)

    def get_nucleus_segments(self) -> list[segment]:
        """
        Return the stored DAPI nucleus masks for this frame.
        """
        return self.__nucleus_segments

    def set_nucleus_segments(self, seg_objs) -> None:
        """
        Store DAPI nucleus masks for this frame.
        """
        self.__nucleus_segments = seg_objs if seg_objs is not None else []
        self.refresh_all_pairings()

    def has_nucleus_segments(self) -> bool:
        """
        Return True when this frame already has DAPI nucleus masks.
        """
        return bool(self.__nucleus_segments)

    def segment_nucleus(self) -> list[segment]:
        """
        Run DAPI nucleus segmentation once and store the resulting masks.
        """
        nucleus_segments = run_nucleus_segmentation(self.__img_np_nucleus, self.gui)
        self.set_nucleus_segments(nucleus_segments)
        return self.get_nucleus_segments()


    def get_segments(self, channel=None) -> list[segment]:
        target_channel = self.__current_channel if channel is None else channel
        if target_channel is None:
            return []
        return self._get_seg_list_for_channel(target_channel)

    def set_segments(self, channel, seg_objs) -> None:
        """Store segment objects for one channel and refresh completion state."""
        target_channel = self.__current_channel if channel is None else channel
        if target_channel is None:
            return
        self._set_seg_list_for_channel(target_channel, seg_objs)
        self.update_pairings_for_channel(target_channel)
        self.segment_generated = self.has_all_channel_segments()

    def has_segments(self, channel=None) -> bool:
        """Return True when the chosen channel already has segmentation masks."""
        return bool(self.get_segments(channel))

    def _get_channels_requiring_segments(self) -> list[str]:
        """Return the channels that must be segmented before the frame is complete."""
        try:
            channels = list(self.available_channels)
        except AttributeError:
            channels = []
        if channels:
            return channels
        if self.__current_channel is None:
            return []
        return [self.__current_channel]

    def has_all_channel_segments(self) -> bool:
        """Return True only when every available channel has segmentation masks."""
        channels = self._get_channels_requiring_segments()
        if not channels:
            return False
        for channel in channels:
            if not self.get_segments(channel):
                return False
        return True

    def segment_channel(self, channel=None) -> list[segment]:
        target_channel = self.__current_channel if channel is None else channel
        if target_channel is None:
            return []
        if not self.bbox_generated:
            self.gui.popBox(
                "w",
                "Bounding Boxes Not Ready",
                "Please generate BBOX before running segmentation.",
            )
            return self.get_segments(target_channel)
        
        nucleus_img = self.__img_np_nucleus
        cyto_channels = {
            "647": self.__img_np_647,
            "488": self.__img_np_488,
            "555": self.__img_np_555,
            "594": self.__img_np_594,
            "514": self.__img_np_514,
        }
        seg_dict = run_cytoplasm_segmentation(nucleus_img, cyto_channels, self.gui, target_channel)
        seg_list = seg_dict.get(target_channel, [])
        self.set_segments(target_channel, seg_list)
        return self.get_segments(target_channel)


    def _set_seg_list_for_channel(self, ch, seg_objs):
        if ch is None:
            return
        seg_list = seg_objs if seg_objs is not None else []
        self.__channel_segments[ch] = seg_list
        if ch == self.__current_channel:
            self.__current_channel_mask = seg_list
    def _get_seg_list_for_channel(self, ch):
        if ch is None:
            return []
        return self.__channel_segments.get(ch, [])

    def _get_mask_list_for_display_channel(self, channel) -> list[segment]:
        """
        Return the visible mask list for the requested display channel.
        """
        if channel == "DAPI":
            return self.get_nucleus_segments()
        return self._get_seg_list_for_channel(channel)

    def _get_rgb_for_channel(self, ch):
        if ch not in self.__channel_rgb_cache:
            if ch == "647" and self.__img_np_647 is not None:
                base_img = self.__img_np_647
            elif ch == "488" and self.__img_np_488 is not None:
                base_img = self.__img_np_488
            elif ch == "555" and self.__img_np_555 is not None:
                base_img = self.__img_np_555
            elif ch == "594" and self.__img_np_594 is not None:
                base_img = self.__img_np_594
            elif ch == "514" and self.__img_np_514 is not None:
                base_img = self.__img_np_514
            else:
                base_img = self.__img_np_nucleus
            self.__channel_rgb_cache[ch] = grayscale_to_rgb(base_img)
        return self.__channel_rgb_cache[ch]

    def _get_rgb_for_display_channel(self, channel):
        """
        Return the RGB image used when the requested display channel is active.
        """
        if channel == "DAPI":
            return grayscale_to_rgb(self.__img_np_nucleus)
        return self._get_rgb_for_channel(channel)

    def getImgNumpyRGBForChannel(self, channel):
        return self._get_rgb_for_display_channel(channel)

    @property
    def current_channel_mask(self):
        return self._get_mask_list_for_display_channel(self.__current_channel)
    @current_channel_mask.setter
    def current_channel_mask(self, value):
        self.set_segments(self.__current_channel, value)


    def set_mask_for_all_channels(self, mask_list):
        """
        Sets the same mask list for all available channels in this frame.
        Used by Apply Channel Mask.
        """
        for ch in self.available_channels:
            self.set_segments(ch, mask_list)

    def get_pairings(self, channel) -> dict:
        """
        Return the stored nucleus-to-cytoplasm pairing for one channel.
        """
        if channel is None:
            return make_empty_pairing_result()
        return self.__channel_pairings.get(channel, make_empty_pairing_result())

    def set_pairings(self, channel, pairing_result: dict) -> None:
        """
        Store the nucleus-to-cytoplasm pairing result for one channel.
        """
        if channel is None:
            return
        self.__channel_pairings[channel] = pairing_result if pairing_result is not None else make_empty_pairing_result()

    def copy_pairings(self, source_channel, target_channels: list[str]) -> None:
        """
        Copy one channel's pairing result to other cytoplasm channels.
        """
        source_pairing = self.get_pairings(source_channel)
        for channel in target_channels:
            self.set_pairings(channel, clone_pairing_result(source_pairing))

    def update_pairings_for_channel(self, channel) -> dict:
        """
        Rebuild the pairing result for one cytoplasm channel.
        """
        segs = self.get_segments(channel)
        pairing_result = build_pairing_result(self.get_nucleus_segments(), segs)
        self.set_pairings(channel, pairing_result)
        return pairing_result

    def refresh_all_pairings(self) -> None:
        """
        Rebuild pairings for every available cytoplasm channel in this frame.
        """
        for channel in self.available_channels:
            if self.get_segments(channel):
                self.update_pairings_for_channel(channel)

# TODO clean code below:

    @bbox.setter
    def bbox(self, value: list[box]):
        self.__bbox = value
        self.bbox_generated = True if value else False
    
    @property
    def boundingBoxRevised(self):
        if self.noBbox():
            return []
        return [b.final for b in self.bbox]
    
    @property
    def bbox_generated(self) -> bool:
        return self.__bbox_generated
    
    @bbox_generated.setter
    def bbox_generated(self, value: bool):
        self.__bbox_generated = value
        if not self.gui.getFuncButton().selectButtonPressed():
            self.thumbnail = "bbox" if value else "default"
    # TODO check where these methods are used and why it is necessary -- update: used in tools_pannels.py, on_channel_change
    @segment.setter
    def segment(self, value):
        self.set_segments(self.__current_channel, value)

    @segment.deleter
    def segment(self):
        self.set_segments(self.__current_channel, [])

    @property # TODO remove if unnecssary, check export in progress.py
    def segmentExplicit(self):
        return self.current_channel_mask
    
    @property
    def segment_generated(self) -> bool:
        return self.__segment_generated
    @segment_generated.setter
    def segment_generated(self, value: bool):
        self.update_thumbnail()
        self.__segment_generated = value
        if not self.gui.getFuncButton().selectButtonPressed():
            self.update_thumbnail()

    # TODO check where each of these methods are used -- remove from set finalized mask in applychhanelmask py
    @property
    def finalized_mask(self):
        return getattr(self, "_finalized_mask", None)
    def set_finalized_mask(self, mask_list: list[np.ndarray]) -> None:
        self._finalized_mask = mask_list  

    @property
    def seg(self):
        return self.current_channel_mask

    @seg.setter
    def seg(self, value):
        self.current_channel_mask = value

    def on_click(self, event):
        """
        Handles what happens to the GUI depending on which mode
        they are in when the user clicks on the thumbnail and sets
        it to focus
        """
        self.gui.getSeasoning().update_channel_selector_for_image(self)
        self.gui.getStove().bufferSetCurrent(3)
        self.gui.getStove().dump()
        from ..services.session_manager import SessionManager
        prev_thumbnail = SessionManager.getBuffer()
        if prev_thumbnail: del prev_thumbnail.highlighted
        self.highlighted = "red"

        func_btn = self.gui.getFuncButton()
        bbox_on = func_btn.bboxButtonPressed()
        seg_on = func_btn.segButtonPressed()

        # --- Select Mode ---
        if func_btn.selectButtonPressed():
            self.selected = not self.selected # calls the selected setter, which then updates the thumbnail_state to "crossout"
        # --- Both BBOX and SEGMENT Mode ---
        elif bbox_on and seg_on:
            if prev_thumbnail:
                prev_thumbnail.drawBbox = False
                prev_thumbnail.drawSegmentation = False
            self.drawBbox = True
            self.drawSegmentation = True
        # --- BBOX Mode ---
        elif bbox_on:
            buffer = box.getBuffer()
            if buffer: buffer.selected = False
            if prev_thumbnail: prev_thumbnail.drawBbox = False
            self.drawBbox = True
        # --- Segment Mode ---
        elif seg_on:
            if prev_thumbnail: prev_thumbnail.drawSegmentation = False
            self.drawSegmentation = True
            
        SessionManager.setBuffer(self)
        self.gui.getStove().cook(self)
    
    def on_multi_toggle(self, event):
        """
        Specifically for multi-selection (Control-click), allowing users to select/deselect 
        multiple images for segmentation without changing focus.

        Args:
        - event : control+click
        """
        if self.gui.getFuncButton().frameSegButtonPressed():
            if not self.bbox_generated:
                self.gui.popBox("w", "BBOX Not Ready", "Generate bounding box before selecting for segmentation.")
                return
            # Only toggle if Control key (0x0004) is pressed
            if event is not None and (event.state & 0x0004):
                self.__selected_for_segmentation = not self.__selected_for_segmentation
                self.update_thumbnail()


    
    # --- Updating Thumbnail --- 
    @property
    def thumbnail(self) -> str:
        return self.__thumbnail_state
    @thumbnail.setter
    def thumbnail(self, value: str): 
        """
        Whenever self.thumbnail_state is assigned a value, this method is called to 
        update the image overlawy
        """
        self.__thumbnail_state = value
        if value == "default":
            self.getLabel().config(image=self.__img_tk_thumbnail)
        elif value == "bbox":
            if not self.__img_tk_thumbnail_bbox:
                self.__img_pil_thumbnail_bbox = self.__img_pil_thumbnail.copy()
                ImageDraw.Draw(self.__img_pil_thumbnail_bbox).ellipse((49, 5, 59, 15), fill=(0,0,255))
                self.__img_tk_thumbnail_bbox = ImageTk.PhotoImage(self.__img_pil_thumbnail_bbox)
            self.getLabel().config(image=self.__img_tk_thumbnail_bbox)
        elif value == "selected":
            if not self.__img_tk_thumbnail_select:
                self.__img_pil_thumbnail_select = self.__img_pil_thumbnail.copy()
                ImageDraw.Draw(self.__img_pil_thumbnail_select).ellipse((5, 5, 15, 15), fill=(0,255,0))
                self.__img_tk_thumbnail_select = ImageTk.PhotoImage(self.__img_pil_thumbnail_select)
            self.getLabel().config(image=self.__img_tk_thumbnail_select)
        elif value == "crossout":
            if not self.__img_tk_thumbnail_crossout:
                self.__img_pil_thumbnail_crossout = self.__img_pil_thumbnail.copy()
                ImageDraw.Draw(self.__img_pil_thumbnail_crossout).line((5, 5, 15, 15), fill=(255,0,0), width=2)
                ImageDraw.Draw(self.__img_pil_thumbnail_crossout).line((5, 15, 15, 5), fill=(255,0,0), width=2)
                self.__img_tk_thumbnail_crossout = ImageTk.PhotoImage(self.__img_pil_thumbnail_crossout)
            self.getLabel().config(image=self.__img_tk_thumbnail_crossout)
        elif value == "segmentation_selected":
            if not self.__img_tk_thumbnail_segmentation_selected:
                self.__img_pil_thumbnail_segmentation_selected = self.__img_pil_thumbnail.copy()
                ImageDraw.Draw(self.__img_pil_thumbnail_segmentation_selected).ellipse((5, 5, 15, 15), fill=(0,255,0))
                ImageDraw.Draw(self.__img_pil_thumbnail_segmentation_selected).ellipse((49, 5, 59, 15), fill=(0,0,255))
                self.__img_tk_thumbnail_segmentation_selected = ImageTk.PhotoImage(self.__img_pil_thumbnail_segmentation_selected)
            self.getLabel().config(image=self.__img_tk_thumbnail_segmentation_selected)
        elif value == "segmented":
            if not self.__img_tk_thumbnail_segmented:
                self.__img_pil_thumbnail_segmented = self.__img_pil_thumbnail_bbox.copy()
                ImageDraw.Draw(self.__img_pil_thumbnail_segmented).ellipse((49, 20, 59, 30), fill=(255, 165, 0))
                self.__img_tk_thumbnail_segmented = ImageTk.PhotoImage(self.__img_pil_thumbnail_segmented)
            self.getLabel().config(image=self.__img_tk_thumbnail_segmented)
        elif value == "segmentation_selected_and_segmented": # TODO unnecessary? same as "segmented"
            if not self.__img_pil_thumbnail_bbox:
                # Create bbox overlay if it doesn't exist
                self.__img_pil_thumbnail_bbox = self.__img_pil_thumbnail.copy()
                ImageDraw.Draw(self.__img_pil_thumbnail_bbox).ellipse((49, 5, 59, 15), fill=(0,0,255))
                self.__img_tk_thumbnail_bbox = ImageTk.PhotoImage(self.__img_pil_thumbnail_bbox)
            if not self.__img_tk_thumbnail_selected_and_segmented:
                self.__img_pil_thumbnail_selected_and_segmented = self.__img_pil_thumbnail_bbox.copy()
                ImageDraw.Draw(self.__img_pil_thumbnail_selected_and_segmented).ellipse((49, 20, 59, 30), fill=(255, 165, 0))
                self.__img_tk_thumbnail_selected_and_segmented = ImageTk.PhotoImage(self.__img_pil_thumbnail_selected_and_segmented)
            self.getLabel().config(image=self.__img_tk_thumbnail_selected_and_segmented)

    @thumbnail.deleter
    def thumbnail(self):
        self.getLabel().pack_forget()

    def update_thumbnail(self):
        self.__img_np_rgb = self._get_rgb_for_channel(self.__current_channel)
        self.__img_pil_thumbnail = Image.fromarray(self.__img_np_rgb).resize((64, 64))
        self.__img_tk_thumbnail = ImageTk.PhotoImage(self.__img_pil_thumbnail)

        # Clear cached overlays so they are rebuilt for the new channel
        self.__img_pil_thumbnail_segmented = None
        self.__img_pil_thumbnail_segmentation_selected = None
        self.__img_pil_thumbnail_selected_and_segmented = None
        self.__img_tk_thumbnail_segmented = None
        self.__img_tk_thumbnail_segmentation_selected = None
        self.__img_tk_thumbnail_selected_and_segmented = None
        
        if self.bbox_generated:
            if self.selected_for_segmentation:
                if self.segment_generated:
                    self.thumbnail = "segmentation_selected_and_segmented"  # blue + orange 
                else:
                    self.thumbnail = "segmentation_selected"  # blue + green
            else:
                if self.segment_generated:
                    self.thumbnail = "segmented"  # blue + orange
                else:
                    self.thumbnail = "bbox"  # blue
        else:
            self.thumbnail = "default"  # no dot


    def _setup_gallery_thumbnail_label_bindings(self, label):
        # Back reference and bring to front
        label._abs = self
        label.lift()

        # Rebuild bindtags: widget tag must come first
        wname = str(label)
        tags = [t for t in label.bindtags() if t != wname]
        tags.insert(0, wname)
        label.bindtags(tuple(tags))

        # Main bindings, add="+" so we don’t overwrite each other
        label.bind("<Button-1>", self.on_click, add="+")
        label.bind("<Button-2>", self.on_click, add="+")
        label.bind("<Button-3>", self.on_click, add="+")
        label.bind("<Control-Button-1>", self.on_multi_toggle, add="+")
        label.bind("<Control-Button-3>", self.on_multi_toggle, add="+")

    # --- Helper functions ---
    @property
    def highlighted(self) -> str:
        return self.__highlighted
    @highlighted.setter
    def highlighted(self, color: str):
        self.__highlighted = color
        self.getLabel().config(borderwidth=2, background=color)
    @highlighted.deleter
    def highlighted(self):
        self.__highlighted = None
        self.getLabel().config(borderwidth=0, background="black")

    @property
    def drawBbox(self) -> bool:
        return self.__drawBbox
    @drawBbox.setter
    def drawBbox(self, value: bool):
        if not self.bbox_generated:
            self.gui.popBox("w", "No BBOX", "No BBOX is available for this image")
            self.__drawBbox = False
            return
        else:
            try:
                for b in self.bbox:
                    try:
                        b.draw = value
                        if not value:
                            box.clearBufferAndDeselect()
                    except Exception as e:
                        logger.warning("Error setting drawBbox for sample %s", self.sample_id, exc_info=True)
                        continue
            except Exception as e:
                logger.warning("Error in drawBbox setter for sample %s", self.sample_id, exc_info=True)
        
        try:
            self.gui.getStove().canvas.draw()
        except Exception as e:
            logger.warning("Error drawing canvas in drawBbox for sample %s", self.sample_id, exc_info=True)
        
        self.__drawBbox = value

    @property
    def drawSegmentation(self) -> bool:
        return self.__drawSeg
    @drawSegmentation.setter
    def drawSegmentation(self, value: bool):
        segs = self.seg if self.segment_generated else []
        stove = self.gui.getStove()
        stove._batch_segment_draw = True
        try:
            for s in segs:
                s.draw = bool(value)
        finally:
            stove._batch_segment_draw = False
        try:
            stove.canvas.draw_idle()
        except Exception:
            pass
        self.__drawSeg = bool(value)

    def findBoxFromPoint(self, x: float, y: float) -> box:
        """
        Determines which bbox object contains the clicked point. 
        Used during editing bbox
        """
        for b in self.bbox:
            if b.contains(x, y):
                return b
        return None
    def findSegFromPoint(self, x: float, y: float) -> segment:
        """
        Determines which segment object contains the clicked point. 
        Used during editing segment
        """
        for s in self.current_channel_mask:
            if s.contains(x, y):
                return s
        return None
    def getImgNumpyRGB(self) -> np.ndarray:
        """
        Used in stove.py and tools_pannel.py
        """
        return self.__img_np_rgb
    def getLabel(self) -> tkinter.Label: # TODO use @property instead like this to ensure consistency: @property /n def label(self):
        """
        Provide access to label so that other methods in the class can update the thumbnail
        """
        return self.__label
    def getNucleusPath(self) -> pathlib.Path:
        return self.__nucleus_path
    def getCytoplasmPaths(self) -> tuple[pathlib.Path, ...]:
        return tuple(self.__cyto_paths)
    #---Remove when refactoring---
    def noBbox(self) -> bool:
        return not len(self.__bbox)
    def noSegment(self) -> bool:
        return not len(self.__current_channel_mask)
    def getNucleusCenters(self) -> list[tuple]:
        return self.nucleus_centers
