"""Defines the main workflow buttons for the FishGUI interface."""

import logging
import pathlib
import threading
import tkinter
import tkinter as tk
from tkinter import filedialog

from ..services.progress import Progress
from ..services.session_manager import SessionManager


logger = logging.getLogger("fishcore")


class funcButton:
    """Builds the main workflow buttons for the multichannel GUI."""

    def __init__(self, gui):
        """Creates the workflow buttons and stores the shared GUI object."""
        self.gui = gui
        self.container = gui.getLowerFrame().getFrameC()
        self.toggle = self._build_toggle_state()
        self._build_buttons()

    def _build_toggle_state(self):
        """Creates the Tk state values used by the checkbutton controls."""
        return {
            "SELECT": tkinter.IntVar(value=0),
            "BBOX": tkinter.IntVar(value=0),
            "SEGMENTATION_SELECTION": tkinter.IntVar(value=0),
            "DISPLAY_MASKS": tkinter.IntVar(value=0),
            "APPLY_CHANNEL_MASK": tkinter.IntVar(value=0),
            "EXPORT": tkinter.IntVar(value=0),
        }

    def _build_buttons(self):
        """Creates every button shown in the main workflow row."""
        self.IMPORT = tkinter.Button(
            self.container,
            text="Import",
            height=2,
            relief=tkinter.RAISED,
            command=self.IMPORT_call,
        )
        self.SELECT = tkinter.Checkbutton(
            self.container,
            text="Select Frames",
            height=2,
            variable=self.toggle["SELECT"],
            onvalue=1,
            offvalue=0,
            indicatoron=False,
            command=self.SELECT_call,
        )
        self.BBOX = tkinter.Checkbutton(
            self.container,
            text="BBOX",
            height=2,
            variable=self.toggle["BBOX"],
            onvalue=1,
            offvalue=0,
            indicatoron=False,
            command=self.BBOX_call,
        )
        self.SEGMENT_NUCLEUS = tkinter.Button(
            self.container,
            text="Segment Nucleus",
            height=2,
            relief=tkinter.RAISED,
            command=self.SEGMENT_NUCLEUS_call,
        )
        self.SEGMENTATION_SELECTION = tkinter.Checkbutton(
            self.container,
            text="Select Cytoplasm Frames",
            height=2,
            variable=self.toggle["SEGMENTATION_SELECTION"],
            onvalue=1,
            offvalue=0,
            indicatoron=False,
            command=self.SEGMENT_SELECTION_call,
        )
        self.SEGMENT = tkinter.Button(
            self.container,
            text="Segment Cytoplasm",
            height=2,
            relief=tkinter.RAISED,
            command=self.SEGMENT_call,
        )
        self.DISPLAY_MASKS = tkinter.Checkbutton(
            self.container,
            text="Edit Masks",
            height=2,
            variable=self.toggle["DISPLAY_MASKS"],
            onvalue=1,
            offvalue=0,
            indicatoron=False,
            command=self.DISPLAY_MASKS_call,
        )
        self.APPLY_CHANNEL_MASK = tkinter.Button(
            self.container,
            text="Copy Channel Mask",
            height=2,
            relief=tkinter.RAISED,
            command=self.APPLY_CHANNEL_MASK_call,
        )
        self.EXPORT = tkinter.Checkbutton(
            self.container,
            text="Export",
            height=2,
            variable=self.toggle["EXPORT"],
            onvalue=1,
            offvalue=0,
            indicatoron=False,
            command=self.EXPORT_call,
        )

    def pack(self):
        """Places the buttons left to right in the main control row."""
        self.IMPORT.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
        self.SELECT.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
        self.SEGMENT_NUCLEUS.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
        self.SEGMENT.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
        self.DISPLAY_MASKS.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)
        self.EXPORT.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X)

    def selectButtonPressed(self) -> bool:
        """Returns True when frame-selection mode is on."""
        return self.toggle["SELECT"].get()

    def bboxButtonPressed(self) -> bool:
        """Returns True when nucleus prompt review mode is active."""
        return self.toggle["BBOX"].get()

    def nucleusPromptModeActive(self) -> bool:
        """Return True when the temporary gdino nucleus prompt mode is active."""
        return self.bboxButtonPressed()

    def frameSegButtonPressed(self) -> bool:
        """Returns True when frame-picking-for-segmentation mode is on."""
        return self.toggle["SEGMENTATION_SELECTION"].get()

    def displayMaskButtonPressed(self) -> bool:
        """Returns True when mask-display mode is on."""
        return self.toggle["DISPLAY_MASKS"].get()

    def IMPORT_call(self):
        """Imports TIFF files and starts background nucleus-center generation."""
        folder_path = filedialog.askdirectory()
        logger.debug("IMPORT_call -> user picked folder: %r", folder_path)
        if not folder_path:
            logger.debug("IMPORT_call -> no folder selected, exiting.")
            return
        folder = pathlib.Path(folder_path)
        tif_files = [file.resolve() for file in folder.glob("*.tif")]
        logger.debug("IMPORT_call -> found %s .tif files", len(tif_files))
        try:
            self.gui.getTifSequence().addToGallery(tif_files)
        except Exception as error:
            logger.exception("IMPORT_call -> addToGallery raised exception")
            self.gui.popBox("e", "Import Error", str(error))
            return
        SessionManager.setImportDirectory(folder)
        if not SessionManager.getPool():
            self.gui.popBox("w", "No Image", "No image is available")
            return
        SessionManager.generate_bboxes(self.gui)

    def SELECT_call(self):
        """Toggles frame-pruning mode for the current gallery pool."""
        if self.selectButtonPressed():
            SessionManager.selectAll()
            return
        SessionManager.removeUnselected()
        self.gui.getTifSequence().resetPosition()
        for abs_obj in SessionManager.getPool():
            self._restore_thumbnail_state(abs_obj)
        SessionManager.sendFirst()

    def BBOX_call(self):
        """Shows or hides nucleus-center overlays for the focused frame."""
        if not self.gui.getStove().isLoaded():
            self.gui.popBox("w", "Image Not Loaded", "Please select an image first")
            self.toggle["BBOX"].set(0)
            return
        focused = SessionManager.getBuffer()
        if focused is None:
            self.gui.popBox("w", "No Image Selected", "Please select an image first")
            self.toggle["BBOX"].set(0)
            return
        if not self.bboxButtonPressed():
            focused.drawBbox = False
            return
        if not focused.bbox_generated:
            self.gui.popBox("w", "Centers Not Ready", "Nucleus centers are not ready yet.")
            self.toggle["BBOX"].set(0)
            return
        focused.drawBbox = True

    def _enter_nucleus_prompt_mode(self, focused):
        """Show editable nucleus prompt boxes for one gdino nucleus run."""
        self.toggle["BBOX"].set(1)
        self.SEGMENT_NUCLEUS.config(text="Run Nucleus Segmentation")
        focused.drawBbox = True
        self.gui.getStove().cook(focused)
        self.gui.popBox(
            "i",
            "Review Nucleus Prompts",
            "Adjust prompt boxes if needed, then click Segment Nucleus again.",
        )

    def _exit_nucleus_prompt_mode(self):
        """Hide nucleus prompt editing and restore the normal button label."""
        focused = SessionManager.getBuffer()
        self.toggle["BBOX"].set(0)
        self.SEGMENT_NUCLEUS.config(text="Segment Nucleus")
        if focused is not None:
            focused.drawBbox = False

    def _run_nucleus_segmentation(self, focused):
        """Run one nucleus segmentation job for the focused sample."""
        self.gui.indicateWait("Nucleus segmentation")

        def job():
            try:
                focused.segment_nucleus()
                self.gui.getRoot().after(0, lambda: self.gui.getStove().cook(focused))
            except Exception as error:
                self.gui.getRoot().after(
                    0,
                    lambda: self.gui.popBox("e", "Nucleus Segmentation Error", str(error)),
                )
            finally:
                self.gui.getRoot().after(0, self.gui.dismissWait)

        threading.Thread(target=job, daemon=True).start()

    def SEGMENT_SELECTION_call(self):
        """Toggles which frames will be used by the Segment action."""
        if self.frameSegButtonPressed():
            return
        for abs_obj in SessionManager.getPool():
            abs_obj.selected_for_segmentation = False
            self._restore_thumbnail_state(abs_obj)

    def _toggle_cytoplasm_frame_selection(self):
        """Start or stop thumbnail selection for the cytoplasm workflow."""
        if self.frameSegButtonPressed():
            self.toggle["SEGMENTATION_SELECTION"].set(0)
            self.SEGMENT_SELECTION_call()
            self.gui.popBox("i", "Select Cytoplasm Frames", "Stopped selecting cytoplasm frames.")
            return
        self._exit_nucleus_prompt_mode()
        self.toggle["SEGMENTATION_SELECTION"].set(1)
        self.gui.popBox(
            "i",
            "Select Cytoplasm Frames",
            "Control-click thumbnails to choose frames for cytoplasm segmentation.",
        )

    def SEGMENT_call(self):
        """Open the cytoplasm workflow choices for segmentation or mask copying."""
        self._exit_nucleus_prompt_mode()
        CytoplasmActionPopup(
            self.gui.getRoot(),
            self._toggle_cytoplasm_frame_selection,
            self._run_cytoplasm_segmentation,
            self.APPLY_CHANNEL_MASK_call,
        )

    def _run_cytoplasm_segmentation(self):
        """Run cytoplasm segmentation for the frames chosen by the user."""
        selected_frames = self._get_selected_frames_for_segmentation()
        if not selected_frames:
            self.gui.popBox(
                "w",
                "No Frames Selected",
                "Please choose frames with Select Cytoplasm Frames first.",
            )
            return
        SessionManager.segment_selected(self.gui)

    def SEGMENT_NUCLEUS_call(self):
        """Run nucleus segmentation for the currently focused sample."""
        focused = SessionManager.getBuffer()
        if focused is None:
            self.gui.popBox("w", "No Image Selected", "Please select an image first")
            return

        if self.nucleusPromptModeActive():
            self._exit_nucleus_prompt_mode()
            self._run_nucleus_segmentation(focused)
            return

        backend_mode = self.gui.prompt_nucleus_backend_mode()
        self.gui.set_nucleus_backend_mode(backend_mode)
        if backend_mode == "gdino_sam":
            self._enter_nucleus_prompt_mode(focused)
            return

        self._run_nucleus_segmentation(focused)

    def DISPLAY_MASKS_call(self):
        """Shows or hides masks for the focused frame without running segmentation."""
        focused = SessionManager.getBuffer()
        if focused is None:
            self.toggle["DISPLAY_MASKS"].set(0)
            self.gui.popBox("w", "No Image Selected", "Please select an image first")
            return
        if self.displayMaskButtonPressed():
            self._exit_nucleus_prompt_mode()
            focused.drawSegmentation = True
            return
        for abs_obj in SessionManager.getPool():
            abs_obj.drawSegmentation = False

    def APPLY_CHANNEL_MASK_call(self):
        """Copies one channel mask to chosen frames and channels."""
        self._reset_modes_before_copy()
        channels = get_apply_channel_source_choices()
        if not channels:
            self.gui.popBox("w", "No Channels", "No cytoplasm channels found in any frame.")
            return
        callback = lambda channel: on_channel_selected(self, channel)
        ChannelSelectPopup(self.gui.getRoot(), channels, callback)

    def EXPORT_call(self):
        """Exports the current session after editing modes are turned off."""
        if not self.gui.getStove().isLoaded():
            tkinter.messagebox.showwarning("Image Not Loaded", "Please select an image first")
            self.toggle["EXPORT"].set(0)
            return
        if self.bboxButtonPressed():
            self._exit_nucleus_prompt_mode()
        if self.displayMaskButtonPressed():
            tkinter.messagebox.showwarning("Edit Masks", "Please turn off Edit Masks before exporting")
            self.toggle["EXPORT"].set(0)
            return
        self.gui.indicateWait("Dataset conversion")

        def job():
            """Runs export work off the main Tk thread."""
            Progress.export(self.gui)
            self.gui.getRoot().after(0, self.gui.dismissWait)

        threading.Thread(target=job, daemon=True).start()

    def _get_selected_frames_for_segmentation(self):
        """Returns the frames that the user marked for segmentation."""
        pool = SessionManager.getPool()
        return [frame for frame in pool if frame.selected_for_segmentation]

    def _restore_thumbnail_state(self, abs_obj):
        """Restores one frame thumbnail after a temporary selection state ends."""
        if abs_obj.segment_generated:
            abs_obj.thumbnail = "segmented"
            return
        if abs_obj.has_nucleus_segments():
            abs_obj.thumbnail = "bbox"
            return
        abs_obj.thumbnail = "default"

    def _reset_modes_before_copy(self):
        """Turns off other view modes before mask-copy workflow starts."""
        self._exit_nucleus_prompt_mode()
        self.toggle["SEGMENTATION_SELECTION"].set(0)
        self.toggle["DISPLAY_MASKS"].set(0)


def start_apply_channel_mask(buttons, selected_channel, frames):
    """Starts the background mask-copy workflow for the chosen frames."""
    buttons.toggle["APPLY_CHANNEL_MASK"].set(1)
    buttons.APPLY_CHANNEL_MASK.config(
        state="disabled",
        relief=tk.SUNKEN,
        text=f"Applying... {selected_channel}",
    )
    buttons.gui.indicateWait(f"Copying channel {selected_channel} mask")

    def on_done():
        """Restores button state after mask-copy workflow finishes."""
        focused = SessionManager.getBuffer()
        if _focused_frame_has_visible_masks(focused):
            buttons.toggle["DISPLAY_MASKS"].set(1)
            focused.drawSegmentation = True
        buttons.gui.dismissWait()
        buttons.toggle["APPLY_CHANNEL_MASK"].set(0)
        buttons.APPLY_CHANNEL_MASK.config(
            state="normal",
            relief=tk.RAISED,
            text="Copy Channel Mask",
        )

    SessionManager.apply_channel_mask_to_frames(
        source_channel=selected_channel,
        selected_frames=frames,
        target_channels="all_channels",
        on_done=on_done,
    )


def _focused_frame_has_visible_masks(focused):
    """Returns True when the focused frame should show masks after copying."""
    if focused is None:
        return False
    if not focused.bbox_generated:
        return False
    return focused.segment_generated or bool(focused.get_segments(focused.selected_channel))


def on_frames_selected(buttons, selected_channel, selection):
    """Validates the chosen target frames before copying masks."""
    frames = get_selected_frames(selection)
    missing = frames_missing_channel(frames, selected_channel)
    if missing:
        show_channel_missing_popup(buttons, selected_channel, missing)
        return
    start_apply_channel_mask(buttons, selected_channel, frames)


def on_channel_selected(buttons, selected_channel):
    """Starts frame selection after the source channel is chosen."""
    if not buffer_has_channel(selected_channel):
        buffer_frame = SessionManager.getBuffer()
        sample_id = buffer_frame.sample_id if buffer_frame is not None else "?"
        buttons.gui.popBox(
            "w",
            "Channel Not Available",
            f"Current frame {sample_id} has no channel {selected_channel}.",
        )
        return
    frame_names = get_frame_names()
    callback = lambda selection: on_frames_selected(buttons, selected_channel, selection)
    FrameSelectPopup(buttons.gui.getRoot(), frame_names, callback)


def buffer_has_channel(channel):
    """Returns True when the focused frame contains the chosen channel."""
    buffer_frame = SessionManager.getBuffer()
    if buffer_frame is None:
        return False
    return channel in buffer_frame.available_channels


def get_apply_channel_source_choices():
    """Returns the channels that are valid sources for copied masks."""
    channels = SessionManager.get_all_available_channels()
    return [channel for channel in channels if channel != "DAPI"]


def get_frame_names():
    """Returns the sample IDs for every loaded frame."""
    return [frame.sample_id for frame in SessionManager.getPool()]


def get_selected_frames(selection):
    """Maps one frame-selection shortcut to the chosen frame objects."""
    pool = SessionManager.getPool()
    if isinstance(selection, list):
        return selection
    if selection == "all":
        return pool
    if selection == "next5":
        buffer_frame = SessionManager.getBuffer()
        start = pool.index(buffer_frame) if buffer_frame in pool else 0
        return pool[start : start + 5]
    return pool


def frames_missing_channel(frames, channel):
    """Returns frame IDs that do not contain the chosen source channel."""
    return [frame.sample_id for frame in frames if channel not in frame.available_channels]


def show_channel_missing_popup(buttons, channel, missing):
    """Shows a short warning when target frames are missing the source channel."""
    preview = ", ".join(missing[:5])
    if len(missing) > 5:
        preview = f"{preview}..."
    buttons.gui.popBox("w", "Channel Not Available", f"Channel {channel} is missing for: {preview}")
    buttons.toggle["DISPLAY_MASKS"].set(0)


class ChannelSelectPopup(tk.Toplevel):
    """Lets the user choose which existing channel mask to copy from."""

    def __init__(self, parent, available_channels, callback):
        """Builds the popup that asks for the source mask channel."""
        super().__init__(parent)
        self.title("Copy Cytoplasm Mask")
        self.callback = callback
        self.selected_channel = tk.StringVar(value=available_channels[0])
        self._build_label()
        self._build_channel_options(available_channels)
        tk.Button(self, text="Next", command=self.on_next).pack(pady=10)

    def _build_label(self):
        """Creates the short instructions shown at the top of the popup."""
        text = (
            "Choose which cytoplasm channel mask to copy from the current frame.\n"
            "That mask will be reused across the cytoplasm frames you pick next."
        )
        tk.Label(self, text=text).pack(pady=10)

    def _build_channel_options(self, available_channels):
        """Creates one radio button for each source channel option."""
        frame = tk.Frame(self)
        frame.pack(pady=10)
        for channel in available_channels:
            label = f"Cytoplasm channel {channel}"
            tk.Radiobutton(frame, text=label, variable=self.selected_channel, value=channel).pack(
                side=tk.LEFT,
                padx=20,
            )

    def on_next(self):
        """Sends the chosen source channel back to the caller."""
        self.callback(self.selected_channel.get())
        self.destroy()


class CytoplasmActionPopup(tk.Toplevel):
    """Let the user choose which cytoplasm action to run next."""

    def __init__(self, parent, select_callback, segment_callback, copy_callback):
        """Build the popup that groups the cytoplasm workflow actions."""
        super().__init__(parent)
        self.title("Segment Cytoplasm")
        self._select_callback = select_callback
        self._segment_callback = segment_callback
        self._copy_callback = copy_callback
        tk.Label(self, text="Choose the next cytoplasm action.").pack(padx=20, pady=12)
        tk.Button(self, text="Select Cytoplasm Frames", command=self._run_select).pack(
            fill="x",
            padx=20,
            pady=4,
        )
        tk.Button(self, text="Run Cytoplasm Segmentation", command=self._run_segmentation).pack(
            fill="x",
            padx=20,
            pady=4,
        )
        tk.Button(self, text="Copy Channel Mask", command=self._run_copy).pack(
            fill="x",
            padx=20,
            pady=(0, 12),
        )

    def _run_select(self):
        """Close the popup and toggle cytoplasm frame selection mode."""
        self.destroy()
        self._select_callback()

    def _run_segmentation(self):
        """Close the popup and start the cytoplasm segmentation path."""
        self.destroy()
        self._segment_callback()

    def _run_copy(self):
        """Close the popup and start the cytoplasm mask copy path."""
        self.destroy()
        self._copy_callback()


class FrameSelectPopup(tk.Toplevel):
    """Lets the user choose which frames should receive copied masks."""

    def __init__(self, parent, frame_names, callback):
        """Builds the popup that asks how many future frames to update."""
        super().__init__(parent)
        self.title("Choose Cytoplasm Frames")
        self.callback = callback
        self.selection = tk.StringVar(value="all")
        tk.Label(self, text="Which cytoplasm frames should receive the copied mask?").pack(pady=10)
        self._build_frame_preview(frame_names)
        self._build_selection_choices()
        tk.Button(self, text="Copy Mask", command=self.on_apply).pack(pady=10)

    def _build_frame_preview(self, frame_names):
        """Shows a short horizontal preview of the available frame IDs."""
        canvas = tk.Canvas(self, height=120)
        scrollbar = tk.Scrollbar(self, orient="horizontal", command=canvas.xview)
        canvas.configure(xscrollcommand=scrollbar.set)
        frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.pack(fill="x")
        scrollbar.pack(fill="x")
        for name in frame_names:
            tk.Label(frame, text=name, relief=tk.RIDGE, width=18).pack(side=tk.LEFT, padx=2, pady=2)
        frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def _build_selection_choices(self):
        """Creates the radio buttons that choose the frame selection size."""
        tk.Radiobutton(self, text="Next 5 Frames", variable=self.selection, value="next5").pack(
            anchor="w",
            padx=20,
        )
        tk.Radiobutton(self, text="All Frames", variable=self.selection, value="all").pack(
            anchor="w",
            padx=20,
        )

    def on_apply(self):
        """Runs the caller callback with the chosen frame selection."""
        try:
            self.callback(self.selection.get())
        except Exception:
            logger.exception("Exception in FrameSelectPopup callback")
        self.destroy()
