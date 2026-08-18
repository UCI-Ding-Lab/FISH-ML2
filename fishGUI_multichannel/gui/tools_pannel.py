import tkinter
import pathlib
import threading
from PIL import Image, ImageTk
from ..services.progress import Progress
from .abstract import abstract as GUIAbstract


class seasoning():
    """Builds the right-side tool panel for viewing and editing masks."""

    def __init__(self, gui):
        """Creates the tool panel widgets and stores the shared GUI object."""
        self.gui = gui
        self.toolbank = tkinter.Frame(self.gui.getLowerFrame().getFrameA(), width=150, background="grey")
        self.button1 = tkinter.Button(self.toolbank, height=2, text="Save Progress", command=self.SAVEPROG_CALL)
        self.button2 = tkinter.Button(self.toolbank, height=2, text="Load Progress", command=self.LOADPROG_CALL)
        self.sep = tkinter.Frame(self.toolbank, height=1, bd=0, relief=tkinter.SUNKEN, bg="black")
        self.seg_editor = tkinter.LabelFrame(self.toolbank, text="Edit Masks")
        icon_path = self._get_icon_path()
        
        self.tools_icon = {"brush": ImageTk.PhotoImage(Image.open(icon_path/"brush.png")),
                           "eraser": ImageTk.PhotoImage(Image.open(icon_path/"eraser.png")),
                           "add_bbox": ImageTk.PhotoImage(Image.open(icon_path/"bbox.png"))}
        
        self.tools_var = {"brush": tkinter.IntVar(value=0),
                          "eraser": tkinter.IntVar(value=0),
                          "add_bbox": tkinter.IntVar(value=0),
                          "add_mask": tkinter.IntVar(value=0)}
        
        self.tools = {"brush": tkinter.Checkbutton(self.seg_editor
                                                   ,image=self.tools_icon["brush"]
                                                   ,variable=self.tools_var["brush"]
                                                   ,onvalue=1,offvalue=0,indicatoron=False
                                                   ,command=lambda: self.press_act("brush")),
                    "eraser": tkinter.Checkbutton(self.seg_editor
                                                    ,image=self.tools_icon["eraser"]
                                                    ,variable=self.tools_var["eraser"]
                                                    ,onvalue=1,offvalue=0,indicatoron=False
                                                    ,command=lambda: self.press_act("eraser")),
                    "add_bbox": tkinter.Button(self.seg_editor
                                               ,image=self.tools_icon["add_bbox"]
                                               ,command=self.ADDBBOX_CALL),
                    "add_mask": tkinter.Button(self.seg_editor
                                               ,text="Add Mask"
                                               ,command=self.ADDMASK_CALL)}
        
        self.marker_size_var = tkinter.IntVar(value=15)
        self.marker_size_scale = tkinter.Scale(self.toolbank,
                                                from_=10,
                                                to=30,
                                                orient=tkinter.HORIZONTAL,
                                                label="Marker Size",
                                                variable=self.marker_size_var
                                            )
        self.sep2 = tkinter.Frame(self.toolbank, height=1, bd=0, relief=tkinter.SUNKEN, bg="black")
        self.contrast_var = tkinter.IntVar(value=250)
        self.contrast_bar = tkinter.Scale(self.toolbank,
                                          from_=0,
                                          to=500,
                                          orient=tkinter.HORIZONTAL,
                                          label="Contrast",
                                          variable=self.contrast_var
                                          )
        self.contrast_bar.bind("<ButtonRelease-1>", self.on_contrast_bar_change)
        self.contrast_reset = tkinter.Button(self.toolbank, text="Reset", command=lambda: self.on_contrast_bar_change(None))
        self.sep3 = tkinter.Frame(self.toolbank, height=1, bd=0, relief=tkinter.SUNKEN, bg="black")
        self.brightness_var = tkinter.IntVar(value=250)
        self.brightness_bar = tkinter.Scale(self.toolbank,
                                             from_=0,
                                             to=500,
                                             orient=tkinter.HORIZONTAL,
                                             label="Brightness",
                                             variable=self.brightness_var
                                            )
        self.brightness_bar.bind("<ButtonRelease-1>", self.on_brightness_bar_change)
        self.brightness_reset = tkinter.Button(self.toolbank, text="Reset", command=lambda: self.on_brightness_bar_change(None))
        self.channel_var = tkinter.StringVar(value="647")
        self.channel_selector = tkinter.OptionMenu(self.toolbank, self.channel_var, "")

    def _get_icon_path(self) -> pathlib.Path:
        """Return the shared GUI icon folder from the app config."""
        config = self.gui.getNucleusBackend().config
        return pathlib.Path(config["gui"]["icon_folder"])

    def pack(self):
        """Places the tool panel widgets on the right side of the window."""
        self.toolbank.pack(side=tkinter.RIGHT, fill=tkinter.BOTH)
        self.button1.pack(side=tkinter.TOP, fill=tkinter.X)
        self.button2.pack(side=tkinter.TOP, fill=tkinter.X)
        self.sep.pack(fill=tkinter.X)
        self.seg_editor.pack(side=tkinter.TOP, fill=tkinter.X)
        self.tools["brush"].grid(row=0, column=0)
        self.tools["eraser"].grid(row=0, column=1)
        self.tools["add_bbox"].grid(row=1, column=0)
        self.tools["add_mask"].grid(row=1, column=1)
        self.marker_size_scale.pack(side=tkinter.TOP, fill=tkinter.X)
        self.sep2.pack(fill=tkinter.X)
        self.contrast_bar.pack(side=tkinter.TOP, fill=tkinter.X)
        self.contrast_reset.pack(side=tkinter.TOP, fill=tkinter.X)
        self.sep3.pack(fill=tkinter.X)
        self.brightness_bar.pack(side=tkinter.TOP, fill=tkinter.X)
        self.brightness_reset.pack(side=tkinter.TOP, fill=tkinter.X)
        self.channel_selector.pack(side=tkinter.TOP, fill=tkinter.X)

    def on_contrast_bar_change(self, event):
        """Adjusts contrast for the currently loaded image preview."""
        if event is None:
            self.contrast_var.set(250)
        contrast_value = self.contrast_var.get()
        factor = (0.01 * contrast_value) - 1.5
        self.gui.getStove().adjust_contrast(factor)
    
    def on_brightness_bar_change(self, event):
        """Adjusts brightness for the currently loaded image preview."""
        if event is None:
            self.brightness_var.set(250)
        brightness_value = self.brightness_var.get()
        factor = (250 - brightness_value) * 0.005
        self.gui.getStove().adjust_brightness(factor)
    
    def get_marker_size(self) -> int:
        """Returns the current brush or eraser radius."""
        return self.marker_size_var.get()

    def brushButtonPressed(self) -> bool:
        """Returns True when the brush tool is active."""
        return self.tools_var["brush"].get()

    def eraserButtonPressed(self) -> bool:
        """Returns True when the eraser tool is active."""
        return self.tools_var["eraser"].get()

    def addMaskButtonPressed(self) -> bool:
        """Return True when the next brush stroke should create a new mask."""
        return self.tools_var["add_mask"].get()
    
    def ADDBBOX_CALL(self):
        """Adds one editable center box to the currently loaded frame."""
        if not self.press_act("add_bbox"):
            return
        if not self.gui.getFuncButton().nucleusPromptModeActive():
            self.gui.popBox("w", "Nucleus Prompt Mode", "Choose GroundingDINO + SAM first")
            return
        loaded_image = self.gui.getStove().getLoaded()
        if not loaded_image:
            self.gui.popBox("w", "No Image", "No image is loaded")
            return
        from .canvas.box import box
        width, height = loaded_image.getImgNumpyRGB().shape[1], loaded_image.getImgNumpyRGB().shape[0]
        bbox = [width // 2 - 150, height // 2 - 150, width // 2 + 150, height // 2 + 150]
        
        # Deselect all existing boxes before adding a new one
        for b in loaded_image.bbox:
            b.selected = False 
        
        new_box = box(bbox, self.gui)
        loaded_image.bbox.append(new_box)
        new_box.selected = True
        new_box.draw = True
        box.setBuffer(new_box)
        self.gui.getStove().canvas.draw()

    def ADDMASK_CALL(self):
        """Prepare one brush stroke that will become a new mask."""
        if not self.press_act("add_mask"):
            return
        self.tools_var["add_mask"].set(1)
        self.tools_var["brush"].set(1)
        self.tools_var["eraser"].set(0)
        self._deactivate_navigation_tool()


    def SAVEPROG_CALL(self):
        """Saves the current session in a background thread."""
        self.gui.indicateWait("Saving")
        def job():
            try:
                Progress.save()
            except Exception as e:
                self.gui.popBox("e", "Save Error", str(e))
            finally:
                self.gui.getRoot().after(0, self.gui.dismissWait)
        threading.Thread(target=job, daemon=True).start()

    def LOADPROG_CALL(self):
        """Loads one saved session in a background thread."""
        self.gui.indicateWait("Loading")
        def job():
            try:
                Progress.load(self.gui)
            except Exception as e:
                self.gui.popBox("e", "Load Error", str(e))
            finally:
                self.gui.getRoot().after(0, self.gui.dismissWait)
        threading.Thread(target=job, daemon=True).start()

    def on_channel_change(self, new_chan: str):
        """
        Switches the focused frame to a new display channel and redraws it.
        """
        self.channel_var.set(new_chan)

        abs_obj = self.gui.getStove().getLoaded()
        if not abs_obj:
            return

        func_btn = self.gui.getFuncButton()
        show_masks = func_btn.displayMaskButtonPressed()
        show_bbox = func_btn.bboxButtonPressed() and new_chan == "DAPI"

        abs_obj.drawSegmentation = False
        abs_obj.drawBbox = False

        abs_obj.selected_channel = new_chan
        self.gui.getStove().cook(abs_obj)

        if show_bbox:
            abs_obj.drawBbox = True
        if show_masks:
            abs_obj.drawSegmentation = True

    def _deactivate_navigation_tool(self):
        """Turns off the Matplotlib navigation tool before mask editing starts."""
        stove = self.gui.getStove()
        toolbar = stove.toolbar
        if toolbar is None:
            return

        try:
            toolbar.clear_active_tool()
        except Exception:
            try:
                toolbar.deactivate_all_tools()
            except Exception:
                pass

    def press_act(self, widget: str):
        """Validates which editing tools are allowed in the current view mode."""
        func_btn = self.gui.getFuncButton()
        bbox_on = func_btn.nucleusPromptModeActive()
        seg_on = func_btn.displayMaskButtonPressed()

        if widget == "add_bbox":
            if not bbox_on or seg_on:
                self.gui.popBox(
                    "w",
                    "Tool Disabled",
                    "Add Box is only available during nucleus prompt review while Edit Masks is off.",
                )
                return False

        if widget == "add_mask":
            if not seg_on or bbox_on:
                self.gui.popBox("w", "Tool Disabled", "Add Mask is only available while Edit Masks is on.")
                return False

        if widget in ("brush", "eraser", "add_mask"):
            if not seg_on or bbox_on:
                self.gui.popBox(
                    "w",
                    "Tool Disabled",
                    "Brush and Eraser are only available while Edit Masks is on and nucleus prompt review is off.",
                )
                for k, v in self.tools_var.items():
                    v.set(0)
                return False

        for k, v in self.tools_var.items():
            if k != widget and not (widget == "add_mask" and k == "brush"):
                v.set(0)

        if widget in ("brush", "eraser") and self.tools_var[widget].get():
            self._deactivate_navigation_tool()

        return True
    
    def update_channel_selector_for_image(self, abs_obj):
        """Syncs the channel dropdown to the newly focused frame."""
        self.update_channel_menu(abs_obj.available_channels)
        self.channel_var.set(abs_obj.selected_channel)

    def update_channel_menu(self, channels: list[str]):
        """Rebuilds the channel dropdown for the currently loaded sample."""
        opts = ["DAPI"] + (channels or [])
        menu = self.channel_selector["menu"]
        menu.delete(0, "end")
        for ch in opts:
            menu.add_command(label=ch, command=lambda v=ch: self.on_channel_change(v))

        cur = self.channel_var.get()
        self.channel_var.set(cur if cur in opts else opts[0])

        self.channel_selector.configure(state="normal" if len(opts) > 1 else "disabled")
