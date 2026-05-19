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
from ..utils.image_preprocessing import (
    normalize_to_uint8,
    grayscale_to_rgb,
    preprocess_nucleus_stack,
    preprocess_cytoplasm_stack,
    remove_outliers,
    clahe,
    gradient
)
from ..services.segmentation import run_basic_watershed, bbox_run_basic_watershed
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class abstract():
    __pool: list['abstract'] = []
    __buffer: 'abstract' = None
    
    def __init__(
        self,
        sample_id, 
        nucleus_path: pathlib.Path,
        cyto_paths: list[pathlib.Path],
        cyto_channels: list[str],
        channels: dict[str, pathlib.Path], # {channel: path}, includes DAPI
        gallery_frame,
        gui
    ):
        self.sample_id = sample_id 
        self.__nucleus_path = nucleus_path
        self.__cyto_paths = cyto_paths
        self.__cyto_channels = cyto_channels
        self.__channels_and_paths = channels
        self.gui = gui

        # Load images
        self.__img_np_nucleus = self._load_nucleus(nucleus_path) # TODO use .resolve() if loading session data generates an error due to path issues; .resolve() ensures absolute path
        self.__img_np_cyto: dict[str, str] = self._load_cytoplasms(channels)
        # Get available channels and set current channel
        self.available_channels = self._get_available_channels()
        if self.available_channels:
            self.selected_channel = self.available_channels[0] # if 647 is present, index 0 points to 647. Otherwise 488
        else:
            self.selected_channel = None
            logger.warning(f"No available cytoplasm channels for sample {self.sample_id} at {nucleus_path}")
        
        # Set __current_channel with appropriate image array
        self.__current_channel = self.__img_np_cyto[self.selected_channel] # Why is self.__current_channel needed?

        # Build thumbnail (647 if exists, else 488. If no channels exists then nucleus)
        if self.selected_channel in self.__cyto_channels:
            thumbnail_img = self.__img_np_cyto[self.selected_channel]
        else:
            thumbnail_img = self.__img_np_nucleus
        
        # Convert image to display on tkinter thumbnail
        self.__img_np_rgb = grayscale_to_rgb(thumbnail_img) # rgb is for displaying image while SAM and groundingdino accepts 2D
        pil = Image.fromarray(self.__img_np_rgb).resize((64, 64))
        tk_img = ImageTk.PhotoImage(pil)
        self.__img_pil_thumbnail = pil # used for image processing, drawing or saving
        self.__img_tk_thumbnail = tk_img # image that will be displayed on gui

        # Set up thumbnail in gui
        self.__label = tkinter.Label(gallery_frame, 
                                     image=tk_img,
                                     width=64, height=64,
                                     relief=tkinter.FLAT, borderwidth=0) # Creates Tkinter Label widget inside gallery_frame container
        self.__label.pack(side=tkinter.LEFT, padx=2, pady=2)
        self.__label.config(width=64, height=64)

        # --- SAFE BIND SETUP -------------------------------------------------
        self.__label._abs = self  # back reference
        self.__label.lift()       # bring to front

        # rebuild bindtags: widget tag must come first
        wname = str(self.__label)
        tags = [t for t in self.__label.bindtags() if t != wname]
        tags.insert(0, wname)
        self.__label.bindtags(tuple(tags))
        print("[thumb] bindtags:", self.__label.bindtags())

        # main bindings, but add="+" so we don’t overwrite each other
        self.__label.bind("<Button-1>", self.on_click, add="+")
        self.__label.bind("<Button-2>", self.on_click, add="+")
        self.__label.bind("<Button-3>", self.on_click, add="+")
        self.__label.bind("<Control-Button-1>", self.on_multi_toggle, add="+")
        self.__label.bind("<Control-Button-3>", self.on_multi_toggle, add="+")

        # debug taps so you can see raw delivery
        def _dbg(seq):
            return lambda e: print(f"[thumb] HIT {seq} num={getattr(e,'num',None)} state={getattr(e,'state',None)}")

        self.__label.bind("<Button-1>", _dbg("<Button-1>"), add="+")
        self.__label.bind("<Button-3>", _dbg("<Button-3>"), add="+")
        self.__label.bind("<Control-Button-1>", _dbg("<Control-Button-1>"), add="+")
        self.__label.bind("<Control-Button-3>", _dbg("<Control-Button-3>"), add="+")
        self.__label.bind("<Enter>", _dbg("<Enter>"), add="+")
  
        # --- Thumbnail variants for different GUI states --- 
        self.__img_pil_thumbnail_bbox = None # image with bbox overlay - blue dot
        self.__img_pil_thumbnail_select = None # image with selection overlay - green dot
        self.__img_pil_thumbnail_crossout = None  # image with crossout overlay - red X
        self.__img_pil_thumbnail_segmented = None # image with segmentation overlay - orange dot
        self.__img_pil_thumbnail_segmentation_selected = None   # image with selection and bbox overlay -- green and blue dot -- TODO : ensure that user cannot select a frame without bbox 
        self.__img_pil_thumbnail_selected_and_segmented = None # image with selection, segmented, bbox overlay - green, blue and orange dot

        self.__img_tk_thumbnail_bbox = None 
        self.__img_tk_thumbnail_select = None
        self.__img_tk_thumbnail_crossout = None
        self.__img_tk_thumbnail_segmented = None
        self.__img_tk_thumbnail_segmentation_selected = None  
        self.__img_tk_thumbnail_selected_and_segmented = None 

        self.__thumbnail_state: str = None # Current thumbnail state TODO check where and how its used

        # --- Boundary boxes ---
        self.__bbox = [] # list of bbox generated for an abstract instance
        self.__bbox_generated: bool = False
        self.__drawBbox: bool = False
        
        # --- Channel-specific segmentation ---
        self.__channel_segs: dict[str, list] = {}
        self.__current_channel_mask = [] # list of segmentation masks - TODO check if segmentation masks for each channels are stored appropriately -- remove if unneessary
        self.__segment_generated: bool = False
        self.__drawSeg: bool = False

        # --- Selection state ---
        self.__selected: bool = True # selected for further evaluation? yes
        self.__selected_for_segmentation: bool = False # selected for segmentation? yes
        self.__highlighted: str = None # focused frame - red border TODO check where its used : def on_click

        from ..services.session_manager import SessionManager
        SessionManager.addToPool(self)

    # --- Helper Functions ---

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
    
    # TODO -  consider separating methods to two : loading and image preprocesing
    def _load_cytoplasms(self, cyto_channels: list[pathlib.Path]) -> dict[str, str]:
        """
        cyto_channels list[str] is used to create a list[image_arrays] for self.__img_np_cyto
        
        Returns the preprocessed image (normalized grayscale) for all channels
        If either channel does not exist, it returns None

        Returns:
        - gray-scale image to ensure compatibility with groundingdino and SAM
        """
        cyto_images = {} # {channel: image}
        for channel, path in cyto_channels.items():
            # Z-Project (if needed)
            cyto_array = tifffile.imread(path)
            zprojected = (
                preprocess_cytoplasm_stack(cyto_array, top_n=8)
                if cyto_array.ndim == 3 and cyto_array.shape[0] > 1
                else np.squeeze(cyto_array)
            )

            # Documented channels are in separate 'if' statements in case they need specific preprocessing
            if "647" in channel:
                img_647 = clahe(normalize_to_uint8(remove_outliers(zprojected, k=20.0, use_median=False)), clip_limit=2.0, tile_size=(8,8))
                cyto_images[channel] = img_647
            elif "488" in channel:
                img_488 = normalize_to_uint8(remove_outliers(zprojected, k=20.0, use_median=False)) 
                img_488 = clahe(img_488, clip_limit=4.0, tile_size=(8,8))
                cyto_images[channel] = img_488
            elif "555" in channel:
                img_555 = normalize_to_uint8(remove_outliers(zprojected, k=20.0, use_median=False)) 
                img_555 = clahe(img_555, clip_limit=4.0, tile_size=(8,8))
                cyto_images[channel] = img_555
            elif "594" in channel:
                img_594 = normalize_to_uint8(remove_outliers(zprojected, k=20.0, use_median=False)) 
                img_594 = clahe(img_594, clip_limit=4.0, tile_size=(8,8))   
                cyto_images[channel] = img_594
            elif "514" in channel:
                img_514 = normalize_to_uint8(remove_outliers(zprojected, k=20.0, use_median=False)) 
                img_514 = clahe(img_514, clip_limit=4.0, tile_size=(8,8))
                cyto_images[channel] = img_514
            else:
                img_undocumented = normalize_to_uint8(remove_outliers(zprojected, k=20.0, use_median=False))
                cyto_images[channel] = img_undocumented

        return cyto_images
    
    def _get_available_channels(self) -> list[str]:
        return self.__cyto_channels

    # --- Selection Logic --- 
    @property
    def selected(self) -> bool:
        return self.__selected
    @selected.setter
    def selected(self, value: bool):
        if value:
            self.thumbnail = "selected" # TODO - thumbnail_state or thumbnail? -- calls setter for thumbnail
            self.__selected = True
        else:
            self.thumbnail = "crossout"
            self.__selected = False

    # --- Boundary Boxes ---
    @property
    def bbox(self):
        """
        Centers calculated and bboxes generated
        """
        if not self.bbox_generated:
            print(f"Generating BBOX for sample {self.sample_id}")
            nuc_boxes = self.gui.getBackEnd().AppIntDINOwrapper(self.__img_np_nucleus)
            centers = [
                ((x0 + x1) / 2, (y0 + y1) / 2)
                for x0, y0, x1, y1 in nuc_boxes
            ]
            self._abstract__nucleus_centers = centers

            # Old Method
            # cyto_boxes = self.gui.getBackEnd().AppIntDINOwrapperB(self.__current_channel, centers)

            # (New Method) --- Creating BBoxes ---
            cyto_boxes = bbox_run_basic_watershed(
                self.__img_np_nucleus, # Nucleus channel
                self.__img_np_cyto, # dict[channel, image_array]
                self.gui,
                self.selected_channel
            )

            boxes = []
            for idx, cbox in enumerate(cyto_boxes):
                center_point = centers[idx] if idx < len(centers) else None
                boxes.append(box(cbox, self.gui, center=center_point))
            self.__bbox = boxes
            self.bbox_generated = True

        return self.__bbox
    
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
    
    # ---  Segmentation Logic ----
    @property
    def segment(self) -> list[segment]:
        """
        Runs when user turns segmentation mode
        """
        # --- Helper ---
        def job():
            self.__channel_segs = run_basic_watershed(
                self.__img_np_nucleus,
                self.__img_np_cyto,
                self.gui,
                self.selected_channel
            )

            # Pick the segmentation mask to use based on currently selected channel
            self.__current_channel_mask = self.__channel_segs[self.selected_channel]
            
            self.segment_generated = True
            logger.info(f"Generated {len(self.__current_channel_mask)} final segments ({self.selected_channel})")
            self.gui.getRoot().after(0, self.gui.dismissWait) # runs after the segemntation is finished. It safely closes the wait dialog
        
        # --- Main logic ---
        if not self.bbox_generated:
            self.gui.popBox("w", "Bounding Boxes Not Ready",
                            "Please generate BBOX before running segmentation.")
            return self.__current_channel_mask

        if not self.segment_generated: # TODO - check that when applychannelmask is called, masks for selected channel is assigned to the other channel variable as well - Ensure that it does not rerun segmentation if mask is already generated to ensure efficiency
            # self.gui.indicateWait("Segmentation")
            self.gui.getRoot().update_idletasks()
            t = threading.Thread(target=job, daemon=True)
            t.start()
            while not self.segment_generated:
                time.sleep(0.1)

        return self.__current_channel_mask
    
    # TODO check where these methods are used and why it is necessary -- update: used in tools_pannels.py, on_channel_change
    @segment.setter
    def segment(self, value):
        self.__current_channel_mask = value
        self.segment_generated = True if value else False

    @segment.deleter
    def segment(self):
        self.__current_channel_mask = []

    @property
    def segmentExplicit(self):
        return self.__current_channel_mask
    
    @property
    def segmentationRevised(self):
        if self.noSegment():
            return []
        return [s._segment__data.T for s in self.segment]
    
    @property
    def segment_generated(self) -> bool:
        return self.__segment_generated
    @segment_generated.setter
    def segment_generated(self, value: bool):
        self.update_thumbnail()
        self.__segment_generated = value
        if not self.gui.getFuncButton().selectButtonPressed():
            self.update_thumbnail()

    # TODO check where each of these methods are used
    @property
    def finalized_mask(self):
        return getattr(self, "_finalized_mask", None)
    def set_finalized_mask(self, mask_list: list[np.ndarray]) -> None:
        self._finalized_mask = mask_list  

    @property
    def seg(self):
        return self.__current_channel_mask

    @seg.setter
    def seg(self, value):
        self.__current_channel_mask = value
    
    @property
    def selected_for_segmentation(self):
        return self.__selected_for_segmentation

    @selected_for_segmentation.setter
    def selected_for_segmentation(self, value):
        self.__selected_for_segmentation = value
        self.update_thumbnail()
    
    def on_click(self, event):
        """
        Handles what happens to the GUI depending on which mode
        they are in when the user clicks on the thumbnail and sets
        it to focus
        """
        if event:
            print("clicked", event.num, event.state)
        self.gui.getSeasoning().update_channel_selector_for_image(self)
        self.gui.getStove().bufferSetCurrent(3)
        self.gui.getStove().dump()
        from ..services.session_manager import SessionManager
        prev_thumbnail = SessionManager.getBuffer()
        if prev_thumbnail: del prev_thumbnail.highlighted
        self.highlighted = "red"

        print(f"select={self.gui.getFuncButton().selectButtonPressed()}, "
        f"frameSeg={self.gui.getFuncButton().frameSegButtonPressed()}, "
        f"bbox={self.gui.getFuncButton().bboxButtonPressed()}, "
        f"seg={self.gui.getFuncButton().segButtonPressed()}, ")

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

    def _get_seg_obj_for_channel(self, ch: str):
        return self.__channel_segs.get(ch, [])

    def _set_seg_obj_for_channel(self, ch: str, seg_objs: list):
        self.__channel_segs[ch] = seg_objs # Assign segmentation masks to specific channel

    # --- Updating Thumbnail --- 
    @property
    def thumbnail(self) -> str:
        return self.__thumbnail_state
    @thumbnail.setter
    def thumbnail(self, value: str): 
        """
        Whenever self.thumbnail is assigned a value, this method is called to 
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
            if not self.__img_tk_thumbnail_selected_and_segmented: 
                self.__img_pil_thumbnail_selected_and_segmented = self.__img_pil_thumbnail_bbox.copy()
                ImageDraw.Draw(self.__img_pil_thumbnail_selected_and_segmented).ellipse((49, 20, 59, 30), fill=(255, 165, 0))
                self.__img_tk_thumbnail_selected_and_segmented = ImageTk.PhotoImage(self.__img_pil_thumbnail_selected_and_segmented)
            self.getLabel().config(image=self.__img_tk_thumbnail_selected_and_segmented)

    @thumbnail.deleter
    def thumbnail(self):
        self.getLabel().pack_forget()

    def update_thumbnail(self):
        # Always rebuild the base thumbnail from the selected channel
        base_img = None
        if self.selected_channel == "647" and self.__img_np_cyto["647"] is not None:
            base_img = self.__img_np_cyto["647"]
            k = 10
        elif self.selected_channel == "488" and self.__img_np_cyto["488"] is not None:
            base_img = self.__img_np_cyto["488"]
            k = 10
        elif self.selected_channel == "555" and self.__img_np_cyto["555"] is not None:
            base_img = self.__img_np_cyto["555"]
            k = 10
        elif self.selected_channel == "594" and self.__img_np_cyto["594"] is not None:
            base_img = self.__img_np_cyto["594"]
            k = 8
        elif self.selected_channel == "514" and self.__img_np_cytp["514"] is not None:
            base_img = self.__img_np_cyto["514"]
            k = 3
        elif self.selected_channel in self.__img_np_cyto:
            base_img = self.__img_np_cyto[self.selected_channel]
            k = 5
        else:
            base_img = self.__img_np_nucleus
            k = 0

        self.__img_np_rgb = grayscale_to_rgb(remove_outliers(base_img, k=k)) if k > 0 else grayscale_to_rgb(base_img)
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


    # --- Helper functions ---
    def getImgNumpyRGBCyto(self, channel) -> np.ndarray:
        """
        Returns the RGB numpy array for the currently selected channel
        """

        if channel in self.__img_np_cyto:
            return grayscale_to_rgb(self.__img_np_cyto[channel])
        else:
            return grayscale_to_rgb(self.__img_np_nucleus)

    def getLabel(self) -> tkinter.Label:
        return self.__label

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
                        print(f"Error setting drawBbox: {e}")
                        continue
            except Exception as e:
                print(f"Error in drawBbox setter: {e}")
        
        try:
            self.gui.getStove().canvas.draw()
        except Exception as e:
            print(f"Error drawing canvas in drawBbox: {e}")
        
        self.__drawBbox = value

    @property
    def drawSegmentation(self) -> bool:
        return self.__drawSeg
    @drawSegmentation.setter
    def drawSegmentation(self, value: bool):
        segs = self.__current_channel_mask if self.segment_generated else []
        for s in segs:
            s.draw = bool(value)
        self.__drawSeg = bool(value)
    
    def findBoxFromPoint(self, x: float, y: float) -> box:
        for b in self.bbox:
            if b.contains(x, y):
                return b
        return None
    def findSegFromPoint(self, x: float, y: float) -> segment:
        for s in self.segment:
            if s.contains(x, y):
                return s
        return None
    def getImgNumpyGreyscale(self) -> np.ndarray:
        return self.__img_np_gs
    def getImgNumpyRGB(self) -> np.ndarray:
        return self.__img_np_rgb
    def getLabel(self) -> tkinter.Label:
        return self.__label
    def getNucleusPath(self) -> pathlib.Path:
        return self.__nucleus_path
    def getImgNumpyCyto(self) -> dict[str, np.ndarray]:
        return dict(self.__img_np_cyto)
    def getCytoplasmPaths(self) -> tuple[pathlib.Path, ...]:
        return tuple(self.__cyto_paths)
    def getCytoplasmChannelsAndPaths(self) -> dict[str, str]:
        return self.__channels_and_paths
    def noBbox(self) -> bool:
        return not len(self.__bbox)
    def noSegment(self) -> bool:
        return not len(self.__current_channel_mask)
    def getNucleusCenters(self) -> list[tuple]:
        return getattr(self, "_abstract__nucleus_centers", []) # TODO - or define self._abstract__nucleus_centers: list[tuple] = []  in init
