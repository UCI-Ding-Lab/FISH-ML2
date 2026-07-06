import tkinter
import pathlib
import logging
from ..services.session_manager import SessionManager
from ..utils.sample_channels import (
    group_files_by_sample_and_channel,
    get_cytoplasm_paths_and_names,
    undocumented_channels_in_grouped,
)

logger = logging.getLogger('fishcore')

"""
Manages the gallery of TIFF image sequences for the GUI.
Handles scrolling, thumbnail display, and grouping by sample/channel.
"""
class tifSequence():
    def __init__(self, gui):
        self.gui = gui
        container = gui.getLowerFrame().getFrameB()
        self.base = tkinter.Canvas(container, height=74)

        self.scrollbar = tkinter.Scrollbar(container, orient=tkinter.HORIZONTAL, command=self.base.xview)
        self.base.configure(xscrollcommand=self.scrollbar.set)

        self.gallery_frame = tkinter.Frame(self.base)
        self.base.create_window((0, 0), window=self.gallery_frame, anchor="nw")

        self.base.bind("<Configure>", lambda e: self.update_scrollregion())
        self.base.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.base.bind_all("<Button-4>", self.on_mouse_wheel)
        self.base.bind_all("<Button-5>", self.on_mouse_wheel)

        # Delegate clicks that Canvas eats back to labels.
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

        def on_parse_error(path: pathlib.Path):
            stem = path.stem
            logger.warning(f"addToGallery → skipping {stem!r}, couldn't parse s### or w###")
            self.gui.popBox(
                "e",
                "File Path Error",
                f"WARNING:\nCouldn't parse file path → skipping {stem!r}, couldn't parse s### or w###",
            )
        # Grouped: {'0026': {'488': WindowsPath('C:/Users/msgal/Downloads/Ding_Lab/image_testing/gui_vadym_single/MAX_EXP_w488_s0026.tif')}}
        # Grouped: {'SAMPLE_ID': {'CHANNEL': pathlib.Path}}
        grouped = group_files_by_sample_and_channel(tif_files, on_parse_error=on_parse_error)
        logger.debug(f"addToGallery → grouped into samples: {list(grouped.keys())}")

        undocumented = undocumented_channels_in_grouped(grouped)
        if undocumented:
            channel_text = ", ".join(undocumented)
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
                except Exception:
                    return "break"
            cur = getattr(cur, "master", None)
        return None