import tkinter
import pathlib
from tkinter import filedialog
import tkinter as tk
import threading
import logging
from ..services.session_manager import SessionManager
from ..services.progress import Progress

logging.basicConfig(
    level=logging.DEBUG,            
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

class funcButton():
    def __init__(self, gui):
        self.gui = gui
        container = gui.getLowerFrame().getFrameC()
        self.toggle = {"SELECT": tkinter.IntVar(value=0),
                       "BBOX": tkinter.IntVar(value=0),
                       "SEGMENTATION_SELECTION" : tkinter.IntVar(value=0),
                       "SEGMENT": tkinter.IntVar(value=0),
                       "APPLY_CHANNEL_MASK" : tkinter.IntVar(value=0),
                       "EXPORT": tkinter.IntVar(value=0)}
        self.IMPORT = tkinter.Button(container,
                                     text="Import",
                                     height=2,
                                     relief=tkinter.RAISED,
                                     command=self.IMPORT_call)
        self.SELECT = tkinter.Checkbutton(container,
                                          text="Select",
                                          height=2,
                                          variable=self.toggle["SELECT"],
                                          onvalue=1,
                                          offvalue=0,
                                          indicatoron=False,
                                          command=self.SELECT_call)
        self.BBOX = tkinter.Checkbutton(container,
                                        text="BBOX",
                                        height=2,
                                        variable=self.toggle["BBOX"],
                                        onvalue=1,
                                        offvalue=0,
                                        indicatoron=False,
                                        command=self.BBOX_call)
        self.SEGMENTATION_SELECTION = tkinter.Checkbutton(container,
                                           text="Segmentation Selection",
                                           height=2,
                                           variable=self.toggle["SEGMENTATION_SELECTION"],
                                           onvalue=1,
                                           offvalue=0,
                                           indicatoron=False,
                                           command=self.SEGMENT_SELECTION_call)
        self.SEGMENT = tkinter.Checkbutton(container,
                                           text="Segment",
                                           height=2,
                                           variable=self.toggle["SEGMENT"],
                                           onvalue=1,
                                           offvalue=0,
                                           indicatoron=False,
                                           command=self.SEGMENT_call)
        self.APPLY_CHANNEL_MASK = tkinter.Button(container,
                                 text="Apply Channel Mask",
                                 height=2,
                                 relief=tkinter.RAISED,
                                 command=self.APPLY_CHANNEL_MASK_call)
        self.EXPORT = tkinter.Checkbutton(container,
                                    text="Export(MATLAB)",
                                    height=2,
                                    variable=self.toggle["EXPORT"],
                                    onvalue=1,
                                    offvalue=0,
                                    indicatoron=False,
                                    command=self.EXPORT_call)

    def pack(self):
        self.IMPORT.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
        self.SELECT.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
        self.BBOX.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
        self.SEGMENTATION_SELECTION.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)  # Place left of SEGMENT
        self.SEGMENT.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
        self.APPLY_CHANNEL_MASK.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
        self.EXPORT.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
    
    def selectButtonPressed(self) -> bool:
        return self.toggle["SELECT"].get()
    def bboxButtonPressed(self) -> bool:
        return self.toggle["BBOX"].get()
    def frameSegButtonPressed(self) -> bool:
        return self.toggle["SEGMENTATION_SELECTION"].get()
    def segButtonPressed(self) -> bool:
        return self.toggle["SEGMENT"].get()
    

    def IMPORT_call(self):
        folder_path = filedialog.askdirectory()
        logger.debug(f"IMPORT_call → user picked folder: {folder_path!r}")
        if not folder_path:
            logger.debug("IMPORT_call → no folder selected, exiting.")
            return

        folder = pathlib.Path(folder_path)
        tif_files = [file.resolve() for file in folder.glob("*.tif")]
        logger.debug(f"IMPORT_call → found {len(tif_files)} .tif files")

        try:
            self.gui.getTifSequence().addToGallery(tif_files) # getTifSequence defined in app.py
        except Exception as e:
            logger.exception("IMPORT_call → addToGallery raised exception")
            self.gui.popBox("e", "Import Error", str(e))
            return
        
        SessionManager.setImportDirectory(folder)
        pool = SessionManager.getPool()
        logger.debug(f"IMPORT_call → abstract pool size after addToGallery: {len(pool)}")
        if len(pool) == 0:
            self.gui.popBox("w", "No Image", "No image is available")
            return

        SessionManager.generate_bboxes(self.gui)


    def SELECT_call(self):
        if self.selectButtonPressed():
            SessionManager.selectAll()
        elif not self.selectButtonPressed():
            SessionManager.removeUnselected()
            self.gui.getTifSequence().resetPosition()
            for abs in SessionManager.getPool():
                abs.thumbnail = "bbox" if abs.bbox_generated else "default"
            SessionManager.sendFirst()


    def BBOX_call(self):
        if not self.gui.getStove().isLoaded():
            self.gui.popBox("w", "Image Not Loaded", "Please select an image first")
            self.toggle["BBOX"].set(0)
            return
        
        abs = SessionManager.getBuffer()
        if not abs:
            self.gui.popBox("w", "No Image Selected", "Please select an image first")
            self.toggle["BBOX"].set(0)
            return
            
        if self.bboxButtonPressed():
            # Entering BBOX mode
            if not abs.bbox_generated:
                self.gui.popBox("w", "Bounding Boxes Not Ready", "Bounding boxes for this image have not been generated yet.")
                self.toggle["BBOX"].set(0)
                return
            abs.drawBbox = True
        else:
            # Exiting BBOX mode
            abs.drawBbox = False
    

    def SEGMENT_SELECTION_call(self):
        if self.segButtonPressed():
            self.toggle["SEGMENT"].set(0)
        if self.frameSegButtonPressed():
            pass
        else:
            # Deselect all frames for segmentation
            for abs_obj in SessionManager.getPool():
                abs_obj.selected_for_segmentation = False
                if abs_obj.segment_generated:
                    abs_obj.thumbnail = "segmented"
                elif abs_obj.bbox_generated:
                    abs_obj.thumbnail = "bbox"
                else:
                    abs_obj.thumbnail = "default"


    def SEGMENT_call(self):
        selected = [a for a in SessionManager.getPool() if a.selected_for_segmentation]
        if self.segButtonPressed():
            if selected:
                SessionManager.segment_selected(self.gui)
                for abs in selected:
                    abs.drawSegmentation = True
            else:
                buf = SessionManager.getBuffer()
                if buf and buf.segment_generated:
                    buf.drawSegmentation = True
        else:
            # Turning OFF: hide segmentation overlays
            for abs_obj in selected:
                abs_obj.drawSegmentation = False
            # Also hide for focused frame if nothing is selected
            if not selected:
                buf = SessionManager.getBuffer()
                if buf and buf.segment_generated:
                    buf.drawSegmentation = False


    def APPLY_CHANNEL_MASK_call(self):
            self.toggle["BBOX"].set(0)
            self.toggle["SEGMENTATION_SELECTION"].set(0)
            self.toggle["SEGMENT"].set(0)
            channels = SessionManager.get_all_available_channels()
            if not channels:
                self.gui.popBox("w", "No Channels", "No available channels found in any frame.")
                return
            ChannelSelectPopup(self.gui.getRoot(), channels, lambda ch: on_channel_selected(self, ch))


# TODO clean below
            
    def EXPORT_call(self):
        # TODO - understand why an image has to be loaded for export
        if not self.gui.getStove().isLoaded():
            tkinter.messagebox.showwarning("Image Not Loaded", "Please select an image first")
            self.toggle["EXPORT"].set(0)
            return
        if self.bboxButtonPressed():
            tkinter.messagebox.showwarning("BBOX Mode", "Please exit BBOX mode first")
            self.toggle["EXPORT"].set(0)
            return
        if self.segButtonPressed():
            tkinter.messagebox.showwarning("Segmentation Mode", "Please exit Segmentation mode first")
            self.toggle["EXPORT"].set(0)
            return
        self.gui.indicateWait("Dataset conversion")
        def job():
            Progress.export(self.gui)
            self.gui.getRoot().after(0, self.gui.dismissWait)
        threading.Thread(target=job, daemon=True).start()



# --- Helper for Apply channek mask ---
def start_apply_channel_mask(self, selected_channel, frames):
    self.toggle["APPLY_CHANNEL_MASK"].set(1)
    self.APPLY_CHANNEL_MASK.config(state="disabled", relief=tk.SUNKEN, text=f"Applying… {selected_channel}")
    self.gui.indicateWait(f"Applying channel {selected_channel} mask…")
    def on_done():
        buf2 = SessionManager.getBuffer()
        if (buf2 and buf2.bbox_generated and
            (buf2.segment_generated or bool(buf2._get_seg_list_for_channel(buf2.selected_channel)))):
            self.toggle["SEGMENT"].set(1)
            buf2.drawSegmentation = True
        else:
            self.toggle["SEGMENT"].set(0)
        self.gui.dismissWait()
        self.toggle["APPLY_CHANNEL_MASK"].set(0)
        self.APPLY_CHANNEL_MASK.config(state="normal", relief=tk.RAISED, text="Apply Channel Mask")
    SessionManager.apply_channel_mask_to_frames(
        source_channel=selected_channel,
        selected_frames=frames,
        target_channels="all_channels",
        on_done=on_done
    )

def on_frames_selected(self, selected_channel, selection):
    frames = get_selected_frames(selection) if isinstance(selection, str) else selection
    missing = frames_missing_channel(frames, selected_channel)
    if missing:
        show_channel_missing_popup(self, selected_channel, missing)
        return
    start_apply_channel_mask(self, selected_channel, frames)


def on_channel_selected(self, selected_channel):
    if not buffer_has_channel(selected_channel):
        buf = SessionManager.getBuffer()
        sid = buf.sample_id if buf else "?"
        self.gui.popBox("w", "Channel Not Available", f"Current frame {sid} has no channel {selected_channel}.")
        return
    frame_names = get_frame_names()
    FrameSelectPopup(self.gui.getRoot(), frame_names, lambda sel: on_frames_selected(self, selected_channel, sel))


def buffer_has_channel(channel):
    buf = SessionManager.getBuffer()
    return buf is not None and channel in buf.available_channels


def get_frame_names():
    return [f.sample_id for f in SessionManager.getPool()]


def get_selected_frames(selection):
    pool = SessionManager.getPool()
    if isinstance(selection, list):
        return selection
    if selection == "all":
        return pool
    elif selection == "next5":
        buf = SessionManager.getBuffer()
        start = pool.index(buf) if buf in pool else 0
        return pool[start:start+5]
    return pool


def frames_missing_channel(frames, channel):
    return [f.sample_id for f in frames if channel not in f.available_channels]


def show_channel_missing_popup(self, channel, missing):
    preview = ", ".join(missing[:5]) + ("..." if len(missing) > 5 else "")
    self.gui.popBox("w", "Channel Not Available", f"Channel {channel} is missing for: {preview}")
    self.toggle["SEGMENT"].set(0)



class ChannelSelectPopup(tk.Toplevel):
    def __init__(self, parent, available_channels, callback):
        super().__init__(parent)
        self.title("Select Channel Mask")
        self.callback = callback
        self.selected_channel = tk.StringVar(value=available_channels[0])

        tk.Label(self, text="Which channel mask do you want to apply for current frame?\n(Chosen channel mask will apply to all channels)").pack(pady=10)

        frame = tk.Frame(self)
        frame.pack(pady=10)
        for ch in available_channels:
            tk.Radiobutton(frame, text=f"Channel {ch}", variable=self.selected_channel, value=ch).pack(side=tk.LEFT, padx=20)

        tk.Button(self, text="Next", command=self.on_next).pack(pady=10)

    def on_next(self):
        self.callback(self.selected_channel.get())
        self.destroy()

class FrameSelectPopup(tk.Toplevel):
    def __init__(self, parent, frame_names, callback):
        super().__init__(parent)
        self.title("Apply Mask To Frames")
        self.callback = callback
        self.selection = tk.StringVar(value="all")

        tk.Label(self, text="How many more frames would you like to add channel masks?").pack(pady=10)

        canvas = tk.Canvas(self, height=120)
        scrollbar = tk.Scrollbar(self, orient="horizontal", command=canvas.xview)
        canvas.configure(xscrollcommand=scrollbar.set)
        frame = tk.Frame(canvas)
        canvas.create_window((0,0), window=frame, anchor="nw")
        canvas.pack(fill="x")
        scrollbar.pack(fill="x")

        for name in frame_names:
            tk.Label(frame, text=name, relief=tk.RIDGE, width=18).pack(side=tk.LEFT, padx=2, pady=2)

        frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

        tk.Radiobutton(self, text="Select Next 5", variable=self.selection, value="next5").pack(anchor="w", padx=20)
        tk.Radiobutton(self, text="Select All Frames", variable=self.selection, value="all").pack(anchor="w", padx=20)

        tk.Button(self, text="Finish & Apply", command=self.on_apply).pack(pady=10)

    def on_apply(self):
        try:
            self.callback(self.selection.get())
        except Exception as e:
            import traceback
            print("Exception in FrameSelectPopup callback:", e)
            traceback.print_exc()
        self.destroy()
