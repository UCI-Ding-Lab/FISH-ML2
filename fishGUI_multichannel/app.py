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

        config_path = pathlib.Path("./config.ini")
        self.__nucleus_backend_mode = self._choose_nucleus_backend_mode()
        self.__cytoplasm_backend_mode = "cellpose_sam"
        self.__nucleus_backend = self._build_nucleus_backend(config_path)
        self.__cytoplasm_backend = self._build_cytoplasm_backend(config_path)

        self.__lf = lf(self)
        self.__tifSequence = tifSequence(self)
        self.__funcButton = funcButton(self)
        self.__seasoning = seasoning(self)
        self.__stove = stove(self)

        self.__lf.pack()
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
            return build_backend(self.__nucleus_backend_mode, config_path)
        except Exception as error:
            self.popBox(
                "e",
                "Backend Load Error",
                f"Failed to start nucleus backend '{self.__nucleus_backend_mode}': {error}",
            )
            raise

    def _build_cytoplasm_backend(self, config_path: pathlib.Path):
        """Build the fixed backend used for cytoplasm segmentation."""
        return build_backend(self.__cytoplasm_backend_mode, config_path)

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

    def getRoot(self) -> tk.Tk:
        """Return the root Tk window."""
        return self.__root

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

def main():
    """Start the multichannel GUI application."""
    root = tk.Tk()
    app = FishGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
