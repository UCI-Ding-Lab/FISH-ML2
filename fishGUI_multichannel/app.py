from tkinter import messagebox
import tkinter as tk
import pathlib
from .backends.factory import build_backend
from .gui.thumbnails import tifSequence
from .gui.buttons import funcButton
from .gui.frames import lf
from .gui.tools_pannel import seasoning
from .gui.canvas.box import box
from .gui.canvas.segment import segment
from .gui.canvas.stove import stove

"""
To run the app: python -m fishGUI_multichannel.app
"""

class FishGUI(object):
    def __init__(self, root):
        """Build the main GUI and create one backend per segmentation role."""
        self.__root: tk.Tk = root
        self.__root.title("FISH UI Prototype")
        self.__root.geometry("870x1000")
        self.__workflow_mode = "neutral"

        self.__config_path = pathlib.Path("./config.ini")
        self.__nucleus_backend_mode = "cellpose_sam"
        self.__cytoplasm_backend_mode = "cellpose_sam"
        self.__nucleus_backend = self._build_nucleus_backend(self.__config_path)
        self.__cytoplasm_backend = self._build_cytoplasm_backend(self.__config_path)

        self.__lf = lf(self)
        self.__mode_banner = self._build_mode_banner()
        self.__tifSequence = tifSequence(self)
        self.__funcButton = funcButton(self)
        self.__seasoning = seasoning(self)
        self.__stove = stove(self)

        self.__lf.pack()
        self.updateModeBanner()
        self.__stove.pack()
        self.__tifSequence.pack()
        self.__funcButton.pack()
        self.__seasoning.pack()

        self.__waitWindow = None

        self._bind_shortcuts()
        self.__root.focus_set()

    def _choose_nucleus_backend_mode(self) -> str:
        """Ask the user which nucleus segmentation backend to use."""
        popup = tk.Toplevel(self.__root)
        popup.title("Choose Nucleus Backend")
        popup.geometry("280x120")
        popup.resizable(False, False)

        choice = tk.StringVar(value="cellpose_sam")

        tk.Label(popup, text="Select nucleus segmentation backend").pack(pady=8)
        tk.Radiobutton(
            popup,
            text="Cellpose-SAM",
            variable=choice,
            value="cellpose_sam",
        ).pack(anchor="w", padx=20)
        tk.Radiobutton(
            popup,
            text="GroundingDINO + SAM",
            variable=choice,
            value="gdino_sam",
        ).pack(anchor="w", padx=20)
        tk.Button(popup, text="Start", command=popup.destroy).pack(pady=10)

        popup.transient(self.__root)
        popup.grab_set()
        self.__root.wait_window(popup)
        return choice.get()

    def _build_nucleus_backend(self, config_path: pathlib.Path):
        """Build the selected nucleus backend and show a readable error if it fails."""
        try:
            return build_backend(self.__nucleus_backend_mode, config_path, "nucleus")
        except Exception as error:
            self.popBox(
                "e",
                "Backend Load Error",
                f"Failed to start nucleus backend '{self.__nucleus_backend_mode}': {error}",
            )
            raise

    def _build_cytoplasm_backend(self, config_path: pathlib.Path):
        """Build the fixed backend used for cytoplasm segmentation."""
        return build_backend(self.__cytoplasm_backend_mode, config_path, "cytoplasm")

    def _build_mode_banner(self) -> tk.Label:
        """Create the small workflow banner that sits in its own stable row."""
        banner = tk.Label(
            self.__lf.getFrameB(),
            text="Main Mode",
            height=1,
            anchor="center",
            justify="center",
            font=("TkDefaultFont", 8, "bold"),
            padx=10,
            pady=2,
            borderwidth=1,
            relief=tk.SOLID,
        )
        banner.pack(fill=tk.X)
        return banner

    def _get_mode_banner_style(self, mode: str) -> tuple[str, str, str]:
        """Return the text and colors used by the centered workflow banner."""
        styles = {
            "neutral": ("Main Mode", "#8B5CF6", "white"),
            "nucleus_gdino": ("Nucleus Mode", "#2563EB", "white"),
            "nucleus_cellpose": ("Nucleus Mode", "#2563EB", "white"),
            "cytoplasm": ("Cytoplasm Mode", "#EA580C", "white"),
        }
        return styles.get(mode, styles["neutral"])

    def prompt_nucleus_backend_mode(self) -> str:
        """Ask the user which backend to use for the next nucleus run."""
        return self._choose_nucleus_backend_mode()

    def set_nucleus_backend_mode(self, mode: str):
        """Store one nucleus backend mode and rebuild that backend when needed."""
        if mode == self.__nucleus_backend_mode:
            return
        self.__nucleus_backend_mode = mode
        self.__nucleus_backend = self._build_nucleus_backend(self.__config_path)

    def _bind_shortcuts(self):
        """Register the keyboard shortcuts used by the GUI."""
        self.__root.bind_all("<Control-z>", self._onUndoShortcut, add="+")
        self.__root.bind_all("<Control-y>", self._onRedoShortcut, add="+")
        self.__root.bind_all("<Control-r>", self._onResetShortcut, add="+")
        self.__root.bind_all("<BackSpace>", self.onDelete, add="+")
        self.__root.bind_all("<Delete>", self.onDelete, add="+")

    def _onUndoShortcut(self, event=None):
        """Undo the last canvas edit and stop the default key handling."""
        self.getStove().onUndo(event)
        return "break"

    def _onRedoShortcut(self, event=None):
        """Redo the last canvas edit and stop the default key handling."""
        self.getStove().onRedo(event)
        return "break"

    def _onResetShortcut(self, event=None):
        """Reset the current canvas edits and stop the default key handling."""
        self.getStove().onReset(event)
        return "break"

    def onDelete(self, event=None):
        """Delete the selected bbox or mask when one is active."""
        selected_box = box.getBuffer()
        selected_seg = segment.getBuffer()
        if selected_box:
            selected_box.delete()
        elif selected_seg:
            selected_seg.delete()
        else:
            self.popBox('w', 'No Selection', 'No bounding box or segmentation mask is selected.')
        return "break"

    def indicateWait(self, content: str):
        """Show a small wait popup while background work is running."""
        self.__waitWindow = tk.Toplevel(self.__root)
        self.__waitWindow.title("FISH-ML")
        self.__waitWindow.geometry("300x100")
        self.__waitWindow.resizable(False, False)
        tk.Label(self.__waitWindow, text=content+" in progress...").pack()

    def dismissWait(self):
        """Close the wait popup when background work finishes."""
        if self.__waitWindow:
            self.__waitWindow.destroy()
            self.__waitWindow = None

    def getLowerFrame(self) -> lf:
        """Return the lower layout frame that holds the controls."""
        return self.__lf

    def getStove(self) -> stove:
        """Return the main image canvas controller."""
        return self.__stove

    def getTifSequence(self) -> tifSequence:
        """Return the thumbnail gallery widget."""
        return self.__tifSequence

    def getFuncButton(self) -> funcButton:
        """Return the main workflow button row."""
        return self.__funcButton

    def getSeasoning(self) -> seasoning:
        """Return the right-side editing panel."""
        return self.__seasoning

    def getNucleusBackend(self):
        """Return the backend used for nucleus centers and nucleus masks."""
        return self.__nucleus_backend

    def getCytoplasmBackend(self):
        """Return the backend used for cytoplasm segmentation."""
        return self.__cytoplasm_backend

    def getNucleusBackendMode(self) -> str:
        """Return the selected backend mode used for nucleus segmentation."""
        return self.__nucleus_backend_mode

    def getCytoplasmBackendMode(self) -> str:
        """Return the fixed backend mode used for cytoplasm segmentation."""
        return self.__cytoplasm_backend_mode

    def setWorkflowMode(self, mode: str):
        """Store the current workflow mode used by the GUI."""
        self.__workflow_mode = mode
        self.updateModeBanner()
        self._refresh_workflow_thumbnails()

    def getWorkflowMode(self) -> str:
        """Return the current workflow mode used by the GUI."""
        return self.__workflow_mode

    def getNucleusWorkflowMode(self) -> str:
        """Return the nucleus workflow mode that matches the chosen backend."""
        if self.__nucleus_backend_mode == "gdino_sam":
            return "nucleus_gdino"
        return "nucleus_cellpose"

    def getRoot(self) -> tk.Tk:
        """Return the root Tk window."""
        return self.__root

    def updateModeBanner(self):
        """Refresh the centered banner so it matches the current workflow mode."""
        text, bg, fg = self._get_mode_banner_style(self.getWorkflowMode())
        self.__mode_banner.config(text=text, bg=bg, fg=fg)
        self.__stove.set_mode_banner(text, bg, fg)

    def _refresh_workflow_thumbnails(self):
        """Refresh every thumbnail so mode-based status dots update together."""
        try:
            from .services.session_manager import SessionManager
            for abs_obj in SessionManager.getPool():
                abs_obj.update_thumbnail()
        except Exception:
            pass

    # ---- popups / status ----
    def popBox(self, level: str, title: str, msg: str):
        """Show a simple info, warning, or error popup."""
        level = (level or "").lower()
        if level.startswith("i"):
            messagebox.showinfo(title, msg, parent=self.__root)
        elif level.startswith("w"):
            messagebox.showwarning(title, msg, parent=self.__root)
        else:
            messagebox.showerror(title, msg, parent=self.__root)

    def ask_use_stored_masks(self, title: str, msg: str) -> bool:
        """Ask whether the user wants to keep the stored masks instead of resegmenting."""
        return messagebox.askyesno(title, msg, parent=self.__root)

def main():
    """Start the multichannel GUI application."""
    root = tk.Tk()
    app = FishGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
