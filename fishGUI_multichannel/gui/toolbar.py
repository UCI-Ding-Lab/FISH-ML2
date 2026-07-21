from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

class FishToolBar(NavigationToolbar2Tk):
    def __init__(self, canvas, window, gui):
        """Create the custom toolbar without letting Matplotlib pack it automatically."""
        super().__init__(canvas, window, pack_toolbar=False)
        self.fishGUI = gui

    def resetToolBank(self):
        """Turn off drawing tools when navigation tools are used."""
        self.fishGUI.getSeasoning().tools_var["brush"].set(0)
        self.fishGUI.getSeasoning().tools_var["eraser"].set(0)
        self.fishGUI.getSeasoning().tools_var["add_mask"].set(0)

    def home(self):
        self.resetToolBank()
        super().home()

    def zoom(self, *args):
        self.resetToolBank()
        super().zoom(*args)

    def deactivate_all_tools(self):
        if self.mode:
            self.mode = ""
            self.set_message("")
            self._update_buttons_checked()

    def is_tool_active(self) -> bool:
        """Return True if a navigation tool (zoom/pan/selector) is active."""
        # NavigationToolbar2Tk uses .mode when zoom/pan active; some variants use _active
        if getattr(self, "mode", ""):
            return True
        if getattr(self, "_active", ""):
            return True
        return False

    def clear_active_tool(self):
        """Clear any active nav tool and reset toolbar UI state."""
        if getattr(self, "mode", ""):
            self.mode = ""
            self.set_message("")
            try:
                self._update_buttons_checked()
            except Exception:
                pass
        # best-effort for alternate attribute
        if getattr(self, "_active", ""):
            try:
                self._active = ""
            except Exception:
                pass

