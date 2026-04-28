import tkinter
import pathlib
import re
import logging
from ..services.session_manager import SessionManager

logger = logging.getLogger(__name__) 

"""
Manages the gallery of TIFF image sequences for the GUI.
Handles scrolling, thumbnail display, and grouping by sample/channel.
"""
class tifSequence():
    def __init__(self, gui):
        self.gui = gui
        container = gui.getLowerFrame().getFrameB()
        self.base = tkinter.Canvas(container, height=74)
        # --- DEBUG: see if Canvas is catching the click ---
        self.base.bind("<Button-1>", lambda e: print("[DEBUG] Canvas got click", e, "at", e.x, e.y, "widget:", e.widget))

        self.scrollbar = tkinter.Scrollbar(container, orient=tkinter.HORIZONTAL, command=self.base.xview)
        self.base.configure(xscrollcommand=self.scrollbar.set)

        self.gallery_frame = tkinter.Frame(self.base)
        self.base.create_window((0, 0), window=self.gallery_frame, anchor="nw")

        self.base.bind("<Configure>", lambda e: self.update_scrollregion())
        self.base.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.base.bind_all("<Button-4>", self.on_mouse_wheel)
        self.base.bind_all("<Button-5>", self.on_mouse_wheel)

        # --- FIX: delegate clicks that Canvas eats back to labels ---
        self.base.bind("<Button-1>", self._delegate_thumb_click, add="+")
        
    def update_scrollregion(self):
        self.base.update_idletasks()
        self.base.config(scrollregion=self.base.bbox("all"))

    def on_mouse_wheel(self, event):
        if event.num == 4:  # Linux scrolling up
            self.base.xview_scroll(-1, "units")
        elif event.num == 5:  # Linux scrolling down
            self.base.xview_scroll(1, "units")
        elif event.delta:  # Windows/macOS
            if event.delta > 0:
                self.base.xview_scroll(-1, "units")
            else:
                self.base.xview_scroll(1, "units")
        
    def pack(self):
        self.base.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)
        self.scrollbar.pack(side=tkinter.BOTTOM, fill=tkinter.X)
    
    def unpack(self):
        self.base.pack_forget()
        self.scrollbar.pack_forget()
    
    def resetPosition(self):
        self.base.xview_moveto(0)
        self.base.yview_moveto(0)

    # Called in buttons.py, IMPORT_call method    
    def addToGallery(self, tif_files: list):
        from .abstract import abstract # prevent circular imports
        logger.debug(f"addToGallery → starting with {len(tif_files)} files")
        documented_channels = {"647", "488", "514", "555", "594"}
        allowed_channels = documented_channels | {"DAPI"}

        def parse_sampleID_and_channel(path: pathlib.Path):
            stem = path.stem
            sample_match = re.search(r"s(\d{1,4})", stem, re.IGNORECASE)
            channel_match = re.search(r"w\d*[-_]?([A-Za-z]*?)(DAPI|\d{3})\D", stem, re.IGNORECASE)
            if not (sample_match and channel_match):
                logger.warning(f"addToGallery → skipping {stem!r}, couldn't parse s### or w###")
                self.gui.popBox("e", "File Path Error", f"WARNING:\nCouldn't parse file path → skipping {stem!r}, couldn't parse s### or w###")
                return None, None
            sample_id = sample_match.group(1)
            channel_name = channel_match.group(2).upper()
            print("Sample_ID:", sample_id, "Channel Name", channel_name)
            return sample_id, channel_name

        def group_files_by_sample_and_channel(file_paths: list):
            """Group files into a dict[sample_id][channel_name] = path."""
            grouped = {}
            for file_path in file_paths:
                path = pathlib.Path(file_path)
                sample_id, channel_name = parse_sampleID_and_channel(path)
                if sample_id and channel_name:
                    grouped.setdefault(sample_id, {})[channel_name] = path
            return grouped
        
        def get_cytoplasm_paths_and_names(channels: dict):
            """Return list of cytoplasm channel paths if present."""
            cyto_paths = []
            cyto_channels = []
            
            for channel, path in channels.items():
                if channel == "DAPI": # Only want cytoplasm paths
                    continue
                cyto_paths.append(path)
                cyto_channels.append(channel)
            return cyto_paths, cyto_channels
        
        # Grouped: {'0026': {'488': WindowsPath('C:/Users/msgal/Downloads/Ding_Lab/image_testing/gui_vadym_single/MAX_EXP_w488_s0026.tif')}}
        # Grouped: {'SAMPLE_ID': {'CHANNEL': pathlib.Path}}
        grouped = group_files_by_sample_and_channel(tif_files)
        print("Grouped:", grouped)
        logger.debug(f"addToGallery → grouped into samples: {list(grouped.keys())}")

        # Warn once per import if any channels are outside the documented set.
        undocumented_channels = sorted(
            {channel for channels in grouped.values() for channel in channels if channel not in allowed_channels}
        )
        if undocumented_channels:
            channel_text = ", ".join(undocumented_channels)
            self.gui.popBox(
                "w",
                "Channel Caution",
                f"CAUTION: The channels [{channel_text}] have not been fully documented and may not have accurate initial segmentation results."
            )
            logger.warning(f"addToGallery → undocumented channels detected: {channel_text}")

        for sample_id, channels in grouped.items():
            nucleus_path = channels.get("DAPI")
            if nucleus_path is None:
                logger.warning(f"addToGallery → sample {sample_id} has no DAPI, skipping")
                continue

            cyto_paths, cyto_channels = get_cytoplasm_paths_and_names(channels)
            print("Cyto paths:", cyto_paths)
            print("Cyto_channels for Sample", cyto_channels)
            logger.info(f"addToGallery → instantiating abstract for sample {sample_id}") # Abstract is initiated for EACH sample_id
            abs_obj = abstract( # Abstract class is called --> where everything begins
                sample_id,
                nucleus_path,
                cyto_paths,
                cyto_channels,
                channels,
                self.gallery_frame,
                self.gui
            )
            self.gui.getSeasoning().update_channel_menu(abs_obj.available_channels)

        SessionManager.sendFirst()
        self.update_scrollregion()
    
    def _delegate_thumb_click(self, event):
        """If the Canvas eats a click, find the Label under the pointer and call its on_click."""
        w = self.base.winfo_containing(event.x_root, event.y_root)
        cur = w
        while cur is not None:
            if hasattr(cur, "_abs"):
                try:
                    return cur._abs.on_click(event)
                except Exception as ex:
                    print("[DEBUG] delegate failed:", ex)
                    return "break"
            cur = getattr(cur, "master", None)
        return None