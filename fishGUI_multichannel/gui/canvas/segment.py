import numpy as np
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from skimage import measure

class segment():
    __buffer: 'segment' = None

    def __init__(self, gui, data: np.ndarray):
        self.__data: np.ndarray = data.T
        self.gui = gui
        self.__patch: PathPatch = None
        self.__draw: bool = False
        self.__exist: bool = True
        self.__selected: bool = False
        
        # history containers
        self._undo_stack = []
        self._redo_stack = []
        # capture original mask for reset
        mask = self._get_mask()
        self._original_mask = mask.copy() if mask is not None else None


    @property
    def xy(self):
        xs, ys = np.where(self.__data.T == 1)
        return xs.min(), ys.min() # TODO -- understand why top left instead of center -- does it affect DOFish compatibility?
    
    @property
    def box(self):
        ys, xs = np.where(self.__data.T == 1)
        return self.__data.T[ys.min():ys.max(), xs.min():xs.max()]

    @property
    def patch(self) -> PathPatch:
        if not self.__patch:
            try:
                c = measure.find_contours(self.__data, level=0.5)[0]
                vertices = np.array(c)
                codes = np.full(len(vertices), Path.LINETO)
                codes[0] = Path.MOVETO
                path = Path(vertices, codes)
                self.__patch = PathPatch(path, facecolor='none', edgecolor='orange', linewidth=0.5)
            except IndexError:
                # If no contours found, create empty patch
                vertices = np.array([[0, 0]])
                codes = np.array([Path.MOVETO])
                path = Path(vertices, codes)
                self.__patch = PathPatch(path, facecolor='none', edgecolor='orange', linewidth=0.5)
        return self.__patch

    @property
    def exist(self) -> bool:
        return self.__exist

    @property
    def selected(self) -> bool:
        return self.__selected
    @selected.setter
    def selected(self, value: bool):
        if self.__selected == value:
            return
        self.__selected = value
        self.draw = False
        self.patch.set_edgecolor('cyan' if value else 'orange')
        canvas = self.gui.getStove().canvas
        subplot = self.gui.getStove().subplot
        background = canvas.copy_from_bbox(subplot.bbox)
        canvas.restore_region(background)
        subplot.draw_artist(self.patch)
        canvas.blit(subplot.bbox)
        self.draw = True

    @property
    def draw(self) -> bool:
        return self.__draw
    @draw.setter
    def draw(self, value: bool):
        if self.__draw == value: 
            return
        try:
            if value:
                self.gui.getStove().subplot.add_patch(self.patch) # Segment Mode: Adding patch
            else:
                try:
                    self.__patch.remove()
                except (NotImplementedError, ValueError, AttributeError):
                    # If normal removal fails, try manual removal from patches list
                    patches = self.gui.getStove().subplot.patches
                    if self.__patch and self.__patch in patches:
                        patches.remove(self.__patch)
        except Exception as e:
            print(f"Error in segment draw setter: {e}")
        
        self.__draw = value
        self.gui.getStove().canvas.draw()

    def contains(self, x: float, y: float) -> bool:
        p = self.gui.getStove().subplot.transData.transform((x, y))
        return self.patch.contains_point(p)

    def update_mask(self, x, y, radius, erase=False):
        print(f"[DEBUG] update_mask called at ({x}, {y}) with radius {radius}, erase={erase}")
        x_int, y_int = int(x), int(y)
        for i in range(x_int - radius, x_int + radius + 1):
            for j in range(y_int - radius, y_int + radius + 1):
                if (i - x_int)**2 + (j - y_int)**2 <= radius**2:
                    if 0 <= i < self.__data.shape[0] and 0 <= j < self.__data.shape[1]:
                        if erase:
                            self.__data[i, j] = 0
                        else:
                            self.__data[i, j] = 1

    def recal_patch(self):
        print("[DEBUG] recal_patch called")
        try:
            c = measure.find_contours(self.__data, level=0.5)[0]
            vertices = np.array(c)
            codes = np.full(len(vertices), Path.LINETO)
            codes[0] = Path.MOVETO
            self.patch.get_path().vertices = vertices
            self.patch.get_path().codes = codes
        except IndexError:
            # If no contours found, set to empty
            pass

    def delete(self):
        abs = self.gui.getStove().getLoaded()
        if abs and self in abs.segment:
            abs.segment.remove(self)
            self.draw = False
            segment.clearBuffer()
            self.gui.getStove().canvas.flush_events()
    
    
    # --- Helper for undo, redo, and reset ---
    def _get_mask(self):
        return getattr(self, "_segment__data", getattr(self, "data", None))

    def _set_mask(self, m):
        if hasattr(self, "_segment__data"):
            self._segment__data = m
        elif hasattr(self, "data"):
            self.data = m

    def _ensure_history(self):
        if not hasattr(self, "_undo_stack"):
            self._undo_stack = []
        if not hasattr(self, "_redo_stack"):
            self._redo_stack = []
        if not hasattr(self, "_original_mask"):
            orig = self._get_mask()
            self._original_mask = orig.copy() if orig is not None else None

    def push_undo(self):
        """Call once at stroke start to snapshot current mask; clears redo."""
        self._ensure_history()
        cur = self._get_mask()
        if cur is None:
            return
        self._undo_stack.append(cur.copy())
        self._redo_stack.clear()

    def undo(self) -> bool:
        self._ensure_history()
        if not self._undo_stack:
            return False
        cur = self._get_mask()
        self._redo_stack.append(cur.copy())
        prev = self._undo_stack.pop()
        self._set_mask(prev.copy())
        # rebuild visual
        try: self.recal_patch()
        except Exception: pass
        return True

    def redo(self) -> bool:
        self._ensure_history()
        if not self._redo_stack:
            return False
        cur = self._get_mask()
        self._undo_stack.append(cur.copy())
        nxt = self._redo_stack.pop()
        self._set_mask(nxt.copy())
        try: self.recal_patch()
        except Exception: pass
        return True

    def reset(self) -> bool:
        self._ensure_history()
        if self._original_mask is None:
            return False
        self._undo_stack.append(self._get_mask().copy())
        self._set_mask(self._original_mask.copy())
        self._redo_stack.clear()
        try: self.recal_patch()
        except Exception: pass
        return True
    
    # -- End of helper for undo, redo and reset --
    @classmethod
    def setBuffer(cls, segment: 'segment'):
        cls.__buffer = segment
    @classmethod
    def getBuffer(cls) -> 'segment':
        return cls.__buffer
    @classmethod
    def clearBuffer(cls):
        cls.__buffer = None
    @classmethod
    def clearBufferAndDeselect(cls):
        current = cls.getBuffer()
        if current: current.selected = False
        cls.__buffer = None