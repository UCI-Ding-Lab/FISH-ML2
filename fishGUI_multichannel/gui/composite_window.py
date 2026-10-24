import tkinter
from tkinter import colorchooser
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from ..services.composite import build_composite, default_channel_colors


def _to_hex(color) -> str:
    """Turn a 0-1 RGB color into the '#rrggbb' text Tk uses for widget colors."""
    return "#%02x%02x%02x" % tuple(round(c * 255) for c in color)


class compositeWindow():
    """
    View-only window showing the colored composite of the frame open in the main canvas.

    It only listens to the main canvas: it follows its frame and zoom/pan, and draws a ring
    where the mouse is. It never changes anything in the main view.
    """

    def __init__(self, gui):
        self.gui = gui
        self.stove = gui.getStove()
        self.window = tkinter.Toplevel(gui.getRoot())
        self.window.title("Composite")
        self.window.geometry("450x600")
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.checkbox_row = tkinter.Frame(self.window)
        self.channel_vars: dict[str, tkinter.IntVar] = {}
        self.chosen_colors = {}  # colors the user picked, by channel; others keep their default
        self.swatches: dict[str, tkinter.Button] = {}

        self.figure = Figure(figsize=(3, 3), dpi=200)
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.subplot = self.figure.add_subplot(111)
        self.subplot.set_axis_off()
        self.canvas = FigureCanvasTkAgg(self.figure, self.window)
        self._setup_view()

        self.checkbox_row.pack(side=tkinter.TOP, fill=tkinter.X)
        self.canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)

        self.canvas.mpl_connect("draw_event", self.on_own_draw)
        self.listeners = [
            self.stove.canvas.mpl_connect("draw_event", self.on_main_draw),
            self.stove.canvas.mpl_connect("motion_notify_event", self.on_main_motion),
        ]
        self.follow_main_view()

    def _setup_view(self):
        """Creates the empty image state and the cursor ring."""
        self.ax_img = None
        self.shown = None  # frame whose composite is on screen
        self.background = None  # composite without the ring, for fast ring redraws
        self.outlines: list[PathPatch] = []  # copies of the main canvas's mask outlines
        self.outline_signature = None  # what the main canvas's outlines looked like at the last copy
        # A marker keeps the same size on screen at any zoom, unlike a Circle sized in image pixels
        (self.cursor,) = self.subplot.plot(
            [], [], marker="o", markersize=5, markerfacecolor="none",
            markeredgecolor="white", markeredgewidth=0.6, animated=True,
        )

    # --- Following the main canvas ---
    def on_main_draw(self, event):
        """Catches up with the main canvas every time it redraws."""
        self.follow_main_view()

    def follow_main_view(self):
        """Shows the main canvas's frame at the same zoom and position."""
        changed = False
        frame = self.stove.getLoaded()
        if frame is not self.shown:
            self.show_frame(frame)
            changed = True
        if frame is not None:
            xlim, ylim = self.stove.subplot.get_xlim(), self.stove.subplot.get_ylim()
            if xlim != self.subplot.get_xlim() or ylim != self.subplot.get_ylim():
                self.subplot.set_xlim(xlim)
                self.subplot.set_ylim(ylim)
                changed = True
        if self._sync_mask_outlines():
            changed = True
        if changed:
            self.canvas.draw_idle()

    def show_frame(self, frame):
        """Replaces the composite with the one for a new frame, or clears it when frame is None."""
        self.shown = frame
        if self.ax_img is not None:
            self.ax_img.remove()
            self.ax_img = None
        if frame is None:
            self._rebuild_checkboxes([])
            return
        self._rebuild_checkboxes(list(frame.getCompositeChannelImages()))
        self.ax_img = self.subplot.imshow(self.make_composite(frame))

    def make_composite(self, frame) -> np.ndarray:
        """Builds the composite of the channels whose checkbox is ticked."""
        images = frame.getCompositeChannelImages()
        visible = {ch: img for ch, img in images.items() if self.channel_vars[ch].get()}
        if not visible:
            shape = next(iter(images.values())).shape
            return np.zeros((*shape, 3), dtype=np.uint8)
        return build_composite(visible, self._colors_for(list(images)))

    # --- Channel checkboxes ---
    def _rebuild_checkboxes(self, channels: list[str]):
        """Shows a checkbox and a color square per channel, keeping each channel's last choices."""
        for widget in self.checkbox_row.winfo_children():
            widget.destroy()
        self.swatches = {}
        colors = self._colors_for(channels)
        for ch in channels:
            if ch not in self.channel_vars:
                self.channel_vars[ch] = tkinter.IntVar(master=self.window, value=1)
            tkinter.Checkbutton(
                self.checkbox_row, text=ch, variable=self.channel_vars[ch], command=self.on_channel_toggle
            ).pack(side=tkinter.LEFT)
            self.swatches[ch] = tkinter.Button(
                self.checkbox_row, width=2, bg=_to_hex(colors[ch]), command=lambda ch=ch: self.pick_color(ch)
            )
            self.swatches[ch].pack(side=tkinter.LEFT, padx=(0, 8))

    def on_channel_toggle(self):
        """Rebuilds the composite after a channel is shown or hidden."""
        if self.ax_img is None:
            return
        self.ax_img.set_data(self.make_composite(self.shown))
        self.canvas.draw_idle()

    def _colors_for(self, channels: list[str]) -> dict:
        """Return each channel's color: the user's pick, or the default."""
        return {**default_channel_colors(channels), **self.chosen_colors}

    def pick_color(self, channel: str):
        """Opens the color picker for one channel and redraws the composite with the new color."""
        current = self._colors_for(list(self.swatches))[channel]
        rgb, _ = colorchooser.askcolor(color=_to_hex(current), parent=self.window, title=f"Color for {channel}")
        if rgb is None:
            return  # cancelled
        self.chosen_colors[channel] = tuple(c / 255 for c in rgb)
        self.swatches[channel].config(bg=_to_hex(self.chosen_colors[channel]))
        self.on_channel_toggle()

    # --- Mask outlines ---
    def _main_mask_outlines(self) -> list[PathPatch]:
        """Return the mask outlines drawn on the main canvas; masks are its only PathPatch shapes."""
        return [p for p in self.stove.subplot.patches if isinstance(p, PathPatch)]

    def _sync_mask_outlines(self) -> bool:
        """Copies the main canvas's mask outlines when they changed. Returns True if it redrew them."""
        main_outlines = self._main_mask_outlines()
        # An edited mask gets a new vertices array, and a selected one turns cyan
        signature = [(id(p), id(p.get_path().vertices), p.get_edgecolor()) for p in main_outlines]
        if signature == self.outline_signature:
            return False
        self.outline_signature = signature
        for outline in self.outlines:
            outline.remove()
        self.outlines = []
        for p in main_outlines:
            path = p.get_path()
            outline = PathPatch(
                Path(path.vertices.copy(), path.codes), facecolor="none",
                edgecolor=p.get_edgecolor(), linewidth=p.get_linewidth(),
            )
            self.subplot.add_patch(outline)
            self.outlines.append(outline)
        return True

    # --- Cursor ring ---
    def on_own_draw(self, event):
        """Saves the freshly drawn composite so the ring can move without a full redraw."""
        self.background = self.canvas.copy_from_bbox(self.subplot.bbox)
        self._draw_cursor()

    def on_main_motion(self, event):
        """Moves the ring to where the mouse is on the main canvas."""
        if self.ax_img is None or self.background is None:
            return
        if event.inaxes is self.stove.subplot and event.xdata is not None:
            self.cursor.set_data([event.xdata], [event.ydata])
        elif len(self.cursor.get_xdata()):
            self.cursor.set_data([], [])
        else:
            return  # ring is already hidden
        self.canvas.restore_region(self.background)
        self._draw_cursor()

    def _draw_cursor(self):
        """Draws only the ring on top of the saved composite."""
        self.subplot.draw_artist(self.cursor)
        self.canvas.blit(self.subplot.bbox)

    # --- Window ---
    def is_open(self) -> bool:
        """Return True while the window has not been closed."""
        return self.window is not None and bool(self.window.winfo_exists())

    def lift(self):
        """Brings the window to the front."""
        self.window.deiconify()
        self.window.lift()

    def close(self):
        """Stops listening to the main canvas and closes the window."""
        for cid in self.listeners:
            self.stove.canvas.mpl_disconnect(cid)
        self.listeners = []
        self.window.destroy()
        self.window = None
