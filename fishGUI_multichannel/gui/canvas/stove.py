import tkinter 
import numpy as np
from matplotlib.figure import Figure 
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.patches import Circle


from ..toolbar import FishToolBar
from .box import box
from .anchor import anchor
from .segment import segment


class stove():
    BILT_BUFFER1 = None
    BILT_BUFFER2 = None
    BILT_BUFFER3 = None
    
    def __init__(self, gui):
        self.gui = gui
        self.pit = tkinter.Frame(self.gui.getLowerFrame().getFrameA(), background="black") # main frame for the canvas
        self.sep = tkinter.Frame(self.gui.getLowerFrame().getFrameA(), width=1, bd=0, relief=tkinter.SUNKEN, bg="black") # separator
        self.mode_banner_frame = tkinter.Frame(self.pit, background="#E5E7EB", pady=2)
        self.mode_banner = tkinter.Label(
            self.mode_banner_frame,
            text="Main Mode",
            height=1,
            anchor="center",
            justify="center",
            font=("TkDefaultFont", 9, "bold"),
            padx=18,
            pady=2,
        )
        
        self.ax_img = None
        self.figure = Figure(figsize=(3,3), dpi=200)
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.subplot = self.figure.add_subplot(111)  # SELF.SUBPLOT
        self.subplot.set_axis_off()
        self.canvas = FigureCanvasTkAgg(self.figure, self.pit)

        # ensure canvas gets focus on click so keyboard shortcuts work
        tk_widget = self.canvas.get_tk_widget()
        tk_widget.bind("<Button-1>", lambda e: e.widget.focus_set(), add='+')
        self.canvas.mpl_connect("button_press_event", self.onCanvasClick)
        self.canvas.mpl_connect("button_release_event", self.onCanvasRelease)
        self.canvas.mpl_connect("motion_notify_event", self.onCanvasDrag)
        self.toolbar = FishToolBar(self.canvas, self.pit, self.gui)
        self.toolbar.update()
        self.tb_pointer = Circle((0, 0), 15, linewidth=0.5, edgecolor='cyan', facecolor='none')
        self.xs = []
        self.ys = []
        self.old_center = None
        self.markers: list[Circle] = []
        self.press = False
        
        self.__onLoad = None

    @property
    def biltbg(self):
        return self.canvas.copy_from_bbox(self.subplot.bbox)
    
    def bufferSetCurrent(self, buffer):
        if buffer == 1:
            self.BILT_BUFFER1 = self.biltbg
        elif buffer == 2:
            self.BILT_BUFFER2 = self.biltbg
        elif buffer == 3:
            self.BILT_BUFFER3 = self.biltbg

    def pack(self):
        self.pit.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True)
        self.sep.pack(side=tkinter.LEFT, fill=tkinter.Y)
        self.canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)
        self.mode_banner_frame.pack(side=tkinter.BOTTOM, fill=tkinter.X)
        self.mode_banner.pack()
        self.toolbar.pack(side=tkinter.BOTTOM, fill=tkinter.BOTH)

    def set_mode_banner(self, text: str, bg: str, fg: str):
        """Update the viewer strip banner text and colors."""
        self.mode_banner_frame.config(background=bg)
        self.mode_banner.config(text=text, bg=bg, fg=fg)

    def _refresh_nucleus_centers(self, abs):
        old_patches = getattr(abs, "_nuc_center_patches", []) or []
        for patch in list(old_patches):
            try:
                patch.remove()
            except Exception:
                pass

        centers = abs.getNucleusCenters() or []
        patches = []
        for cx, cy in centers:
            try:
                cpatch = Circle((cx, cy), radius=5, color='lime', fill=True)
                self.subplot.add_patch(cpatch)
                patches.append(cpatch)
            except Exception:
                continue
        abs._nuc_center_patches = patches
        
    def cook(self, abs):
        if self.getLoaded() is abs and self.ax_img is not None:
            self.ax_img.set_data(abs.getImgNumpyRGB())
            self._refresh_nucleus_centers(abs)
            self.subplot.set_axis_off()
            self.canvas.draw_idle()
            return

        self.setLoaded(abs)
        self.ax_img = self.subplot.imshow(self.getLoaded().getImgNumpyRGB())
        self.subplot.set_axis_off()
        self._refresh_nucleus_centers(abs)
        self.canvas.draw()

    def dump(self):
        self.clearLoaded()
        # Clear all patches safely
        try:
            if hasattr(self.subplot, 'patches'):
                # Create a copy of the patches list to avoid modification during iteration
                patches_to_remove = list(self.subplot.patches)
                for patch in patches_to_remove:
                    try:
                        patch.remove()
                    except (NotImplementedError, ValueError, AttributeError):
                        # If removal fails, just continue
                        pass
                # Clear the patches list completely
                self.subplot.patches.clear()
        except AttributeError:
            pass
        
        self.subplot.clear()
        self.subplot.set_axis_off()
        self.canvas.draw()
    
    def adjust_contrast(self, factor):
        img = self.getLoaded().getImgNumpyRGB()
        img = img.astype(np.float32) / 255.0
        img = np.clip(0.5 + factor * (img - 0.5), 0, 1)
        img = (img * 255).astype(np.uint8)
        self.ax_img.set_data(img)
        self.canvas.draw()
    
    def adjust_brightness(self, factor):
        img = self.getLoaded().getImgNumpyRGB()
        img = img.astype(np.float32) / 255.0
        img = np.clip(factor + img, 0, 1)
        img = (img * 255).astype(np.uint8)
        self.ax_img.set_data(img)
        self.canvas.draw()
        
    def onCanvasClick(self, event: MouseEvent):
        # do not allow new selection if toolbar is active
        try:
            if self.toolbar.is_tool_active():
                return
        except Exception:
            pass

        self.canvas.get_tk_widget().focus_set()  # ensure that any click on the canvas will receive keyboard events
        self.press = True
        if stove.isLeftClick(event):
            if event.inaxes != self.subplot:
                return
                
            # Handle BBOX mode interactions
            if self.gui.getFuncButton().bboxButtonPressed():
                if box.getBuffer() and box.getBuffer().selected:
                    anchorName = box.getBuffer().anchorContains(event.xdata, event.ydata) # Anchor stores bboxes, uses x and y finds the specific box

                    if anchorName:
                        target = box.getBuffer().anchors[anchorName]
                        target.selected = True
                        anchor.setBuffer(target)

                        b = box.getBuffer()
                        if self.old_center is None:
                            self.old_center = b.center
                        b.removeCenter(self.gui, self.old_center)

                        return
                target = self.getLoaded().findBoxFromPoint(event.xdata, event.ydata) 
                box.clearBufferAndDeselect()
                if target:
                    self.toolbar.deactivate_all_tools()
                    target.selected = True
                    box.setBuffer(target)
                    return  # Exit early if we found a box
                    
            # Handle SEGMENT mode interactions (only if not handled by bbox above)
            if self.gui.getFuncButton().displayMaskButtonPressed():
                brush_active = self.gui.getSeasoning().brushButtonPressed()
                eraser_active = self.gui.getSeasoning().eraserButtonPressed()
                buf = segment.getBuffer()
                # Handle brush/eraser tools
                # If brush/eraser tool is active, DO NOT change selection on click.
                # Only begin a stroke if there is an already-selected segment AND
                # the click is within that selected segment. This prevents accidental
                # switching to overlapping segments while editing.
                if brush_active or eraser_active:
                    edit_margin = max(2, min(6, int(self.gui.getSeasoning().get_marker_size() / 2)))
                    if buf and buf.selected and buf.contains(event.xdata, event.ydata, margin=edit_margin):
                        try:
                            buf.push_undo() # record undo snapshot at the start of the stroke if available
                        except Exception:
                                pass
                        self.xs = [event.xdata]
                        self.ys = [event.ydata]
                        self.bufferSetCurrent(1)
                        self.bufferSetCurrent(2)
                        try:
                            self.canvas.restore_region(self.BILT_BUFFER1)
                        except Exception:
                            pass
                        self.marker_draw(event.xdata, event.ydata)
                        try:
                            self.canvas.blit(self.subplot.bbox)
                        except Exception:
                            pass
                    else:
                        # ignore click when brush/eraser active but no valid selected buffer
                        self.press = False
                        return
                else:
                    # Normal selection behavior (only when NOT in brush/eraser mode)
                    target = self.getLoaded().findSegFromPoint(event.xdata, event.ydata)
                    segment.clearBufferAndDeselect()
                    if target:
                        target.selected = True
                        segment.setBuffer(target)

    def onCanvasRelease(self, event: MouseEvent):
        self.press = False
        if self.gui.getFuncButton().bboxButtonPressed():
            anchor.clearBuffer()
            self.old_center = None
        elif self.gui.getFuncButton().displayMaskButtonPressed():
            if self.gui.getSeasoning().brushButtonPressed() and segment.getBuffer() and segment.getBuffer().selected:
                final = list(zip(self.xs, self.ys))
                for marker in self.markers:
                    marker.remove()
                self.markers.clear()
                for x, y in final:
                    segment.getBuffer().update_mask(x, y, self.gui.getSeasoning().get_marker_size())
                segment.getBuffer().recal_patch()
                self.canvas.draw_idle()
                self.xs.clear()
                self.ys.clear()
            elif self.gui.getSeasoning().eraserButtonPressed() and segment.getBuffer() and segment.getBuffer().selected:
                final = list(zip(self.xs, self.ys))
                for marker in self.markers:
                    marker.remove()
                self.markers.clear()
                for x, y in final:
                    segment.getBuffer().update_mask(x, y, self.gui.getSeasoning().get_marker_size(), erase=True)
                segment.getBuffer().recal_patch()
                self.canvas.draw_idle()
                self.xs.clear()
                self.ys.clear()

    def onCanvasDrag(self, event: MouseEvent):
        if not self.press: 
            return
        if self.gui.getFuncButton().bboxButtonPressed():
            a = anchor.getBuffer()
            b = box.getBuffer()
            if not (a and a.selected and b and b.selected): 
                return
            if event.inaxes != b.rect.axes: 
                return
            
            x0, y0 = b.rect.get_xy()
            w, h = b.rect.get_width(), b.rect.get_height()
            
            if a.location == "bottom-left":
                nx, ny = event.xdata, event.ydata
                w += x0 - nx
                h += y0 - ny
                b.rect.set_xy((nx, ny))
            elif a.location == "bottom-right":
                w = event.xdata - x0
                h += y0 - event.ydata
                b.rect.set_xy((x0, event.ydata))
            elif a.location == "top-right":
                w = event.xdata - x0
                h = event.ydata - y0
            elif a.location == "top-left":
                nx = event.xdata
                h = event.ydata - y0
                w += x0 - nx
                b.rect.set_xy((nx, y0))
            elif a.location == "pos-anchor":
                dx = event.xdata - (b.rect.get_x() + w/2)
                dy = event.ydata - (b.rect.get_y() + h)
                b.rect.set_xy((x0 + dx, y0 + dy))
            
            b.rect.set_width(w)
            b.rect.set_height(h)
            new_center = b.rect.get_center()
            b.center = new_center # Successfully adds dot once bbox is clicked out
            b.anchorUpdate()
            self.canvas.draw()

        elif self.gui.getFuncButton().displayMaskButtonPressed() and segment.getBuffer() and segment.getBuffer().selected:
            current_x, current_y = event.xdata, event.ydata
            if current_x is None or current_y is None: 
                return

            if self.gui.getSeasoning().brushButtonPressed() or self.gui.getSeasoning().eraserButtonPressed():
                x_vals = [current_x]
                y_vals = [current_y]
                if self.xs and self.ys:
                    lx, ly = self.xs[-1], self.ys[-1]
                    distance = np.hypot(current_x - lx, current_y - ly)
                    if distance > 5:
                        n = int(distance // 1)
                        x_vals = np.linspace(lx, current_x, n + 1)
                        y_vals = np.linspace(ly, current_y, n + 1)
                for i, (x, y) in enumerate(zip(x_vals, y_vals)):
                    self.xs.append(x)
                    self.ys.append(y)
                    self.bufferSetCurrent(1)
                    if i % 3 == 0:
                        self.canvas.restore_region(self.BILT_BUFFER1)
                        self.marker_draw(x, y)
                        self.canvas.blit(self.subplot.bbox)
                else:
                    self.xs.append(current_x)
                    self.ys.append(current_y)
                    self.bufferSetCurrent(1)
                    self.canvas.restore_region(self.BILT_BUFFER1)
                    self.marker_draw(current_x, current_y)
                    self.canvas.blit(self.subplot.bbox)

    def marker_draw(self, x, y):
        circle = Circle((x, y), self.gui.getSeasoning().get_marker_size(), color='red', alpha=0.01)
        self.markers.append(circle)
        self.subplot.add_patch(circle)
        self.subplot.draw_artist(circle)

    def isLoaded(self) -> bool:
        return self.__onLoad is not None
    def getLoaded(self):
        return self.__onLoad
    def setLoaded(self, abs):
        self.__onLoad = abs
    def clearLoaded(self):
        self.__onLoad = None

    def onUndo(self, event=None):
        if not self.gui.getFuncButton().displayMaskButtonPressed():
            return
        loaded = self.getLoaded()

        ok = False
        try:
            ok = segment.undo_latest_action(loaded)
        except Exception:
            ok = False

        if ok:
            try:
                self.canvas.draw_idle()
            except Exception:
                pass
        else:
            try:
                self.gui.popBox("i", "Undo", "Nothing to undo")
            except Exception:
                pass


    def onRedo(self, event=None):
        if not self.gui.getFuncButton().displayMaskButtonPressed():
            return
        loaded = self.getLoaded()

        ok = False
        try:
            ok = segment.redo_latest_action(loaded)
        except Exception:
            ok = False

        if ok:
            try:
                self.canvas.draw_idle()
            except Exception:
                pass
        else:
            try:
                self.gui.popBox("i", "Redo", "Nothing to redo")
            except Exception:
                pass


    def onReset(self, event=None):
        if not self.gui.getFuncButton().displayMaskButtonPressed():
            return
        loaded = self.getLoaded()

        ok = False
        try:
            ok = segment.reset_loaded(loaded)
        except Exception:
            ok = False

        if ok:
            try:
                self.canvas.draw_idle()
            except Exception:
                pass
        else:
            try:
                self.gui.popBox("i", "Reset", "Nothing to reset")
            except Exception:
                pass

     
    @staticmethod
    def isLeftClick(event: MouseEvent) -> bool:
        return event.button == 1
