import logging
import pathlib
import tkinter

from ..services.session_manager import SessionManager
from ..utils.sample_channels import (
    group_files_by_sample_and_channel,
    undocumented_channels_in_grouped,
)

logger = logging.getLogger("fishcore")


class tifSequence():
    """Manage the thumbnail gallery for imported TIFF image samples."""

    def __init__(self, gui):
        """Create the scrollable gallery canvas and connect mouse bindings."""
        self.gui = gui
        container = gui.getLowerFrame().getFrameB()
        self.base = tkinter.Canvas(container, height=74)
        self.scrollbar = tkinter.Scrollbar(container, orient=tkinter.HORIZONTAL, command=self.base.xview)
        self.base.configure(xscrollcommand=self.scrollbar.set)
        self.gallery_frame = tkinter.Frame(self.base)
        self.base.create_window((0, 0), window=self.gallery_frame, anchor="nw")
        self._bind_gallery_events()

    def _bind_gallery_events(self) -> None:
        """Connect canvas resize, scroll, and thumbnail click handlers."""
        self.base.bind("<Configure>", lambda event: self.update_scrollregion())
        self.base.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.base.bind_all("<Button-4>", self.on_mouse_wheel)
        self.base.bind_all("<Button-5>", self.on_mouse_wheel)
        self.base.bind("<Button-1>", self._delegate_thumb_click, add="+")

    def update_scrollregion(self):
        """Refresh the scroll bounds after thumbnails are added or removed."""
        self.base.update_idletasks()
        self.base.config(scrollregion=self.base.bbox("all"))

    def on_mouse_wheel(self, event):
        """Move the gallery horizontally when the user scrolls."""
        button_number = self._event_button_number(event)
        scroll_delta = self._event_scroll_delta(event)
        if button_number == 4 or scroll_delta > 0:
            self.base.xview_scroll(-1, "units")
            return
        if button_number == 5 or scroll_delta < 0:
            self.base.xview_scroll(1, "units")

    def _event_button_number(self, event) -> int | None:
        """Return the platform-specific mouse button number from a Tk event."""
        try:
            return event.num
        except AttributeError:
            return None

    def _event_scroll_delta(self, event) -> int:
        """Return the platform-specific wheel delta from a Tk event."""
        try:
            return event.delta
        except AttributeError:
            return 0

    def pack(self):
        """Show the gallery canvas and its horizontal scrollbar."""
        self.base.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)
        self.scrollbar.pack(side=tkinter.BOTTOM, fill=tkinter.X)

    def unpack(self):
        """Hide the gallery canvas and scrollbar."""
        self.base.pack_forget()
        self.scrollbar.pack_forget()

    def resetPosition(self):
        """Return the gallery scroll position to the beginning."""
        self.base.xview_moveto(0)
        self.base.yview_moveto(0)

    def addToGallery(self, tif_files: list):
        """Add imported TIFF files to the thumbnail gallery by sample."""
        from .abstract import abstract

        grouped = group_files_by_sample_and_channel(tif_files, on_parse_error=self._show_parse_error)
        self._show_undocumented_channel_warning(grouped)
        for sample_id, channels in grouped.items():
            self._add_sample_to_gallery(sample_id, channels, abstract)
        SessionManager.sendFirst()
        self.update_scrollregion()

    def _show_parse_error(self, path: pathlib.Path) -> None:
        """Show a warning when one file name cannot be parsed."""
        stem = path.stem
        logger.warning("addToGallery -> skipping %r, could not parse sample/channel", stem)
        self.gui.popBox("e", "File Path Error", f"Could not parse sample/channel from {stem!r}")

    def _show_undocumented_channel_warning(self, grouped: dict) -> None:
        """Warn when imported channels do not have tuned preprocessing defaults."""
        undocumented = undocumented_channels_in_grouped(grouped)
        if not undocumented:
            return
        channel_text = ", ".join(undocumented)
        self.gui.popBox("w", "Channel Caution", f"Channels [{channel_text}] may not have tuned segmentation defaults.")
        logger.warning("addToGallery -> undocumented channels detected: %s", channel_text)

    def _add_sample_to_gallery(self, sample_id: str, channels: dict, abstract_cls) -> None:
        """Create one frame object for a grouped sample."""
        nucleus_path = channels.get("DAPI")
        if nucleus_path is None:
            logger.warning("addToGallery -> sample %s has no DAPI, skipping", sample_id)
            return
        logger.info("addToGallery -> instantiating abstract for sample %s", sample_id)
        abs_obj = abstract_cls(sample_id, nucleus_path, channels, self.gallery_frame, self.gui)
        self.gui.getSeasoning().update_channel_menu(abs_obj.available_channels)

    def _delegate_thumb_click(self, event):
        """Forward canvas clicks to the thumbnail object under the pointer."""
        cur = self.base.winfo_containing(event.x_root, event.y_root)
        while cur is not None:
            try:
                return cur._abs.on_click(event)
            except AttributeError:
                cur = self._get_parent_widget(cur)
            except Exception:
                return "break"
        return None

    def _get_parent_widget(self, widget):
        """Return a widget's parent, or None when there is no parent."""
        try:
            return widget.master
        except AttributeError:
            return None
