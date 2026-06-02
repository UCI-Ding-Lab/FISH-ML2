import logging
import numpy as np
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from skimage import measure

logger = logging.getLogger('fishcore')

class segment():
    __buffer: 'segment' = None
    __deleted_stack = []
    __action_history = []
    __redo_actions = []

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
        self.patch.set_edgecolor('cyan' if value else 'orange')

        stove = self.gui.getStove()
        loaded = stove.getLoaded()
        if loaded is None:
            return

        # Only redraw immediately if this segment belongs to the frame/channel
        # currently shown on screen. Otherwise, just keep the color state updated
        # and let the normal frame/channel redraw path render it later.
        if self not in loaded.current_channel_mask:
            return

        try:
            if self.patch.axes is stove.subplot:
                stove.canvas.draw_idle()
        except Exception:
            pass

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
        except Exception:
            logger.warning("Error in segment draw setter", exc_info=True)
        
        self.__draw = value
        stove = self.gui.getStove()
        if not getattr(stove, "_batch_segment_draw", False):
            stove.canvas.draw()

    def contains(self, x: float, y: float, margin: int = 0) -> bool:
        if x is None or y is None:
            return False

        if margin <= 0:
            p = self.gui.getStove().subplot.transData.transform((x, y))
            return self.patch.contains_point(p)

        x0 = max(0, int(np.floor(x - margin)))
        x1 = min(self.__data.shape[0], int(np.ceil(x + margin)) + 1)
        y0 = max(0, int(np.floor(y - margin)))
        y1 = min(self.__data.shape[1], int(np.ceil(y + margin)) + 1)

        if x0 >= x1 or y0 >= y1:
            return False

        xs, ys = np.ogrid[x0:x1, y0:y1]
        within_margin = (xs - x) ** 2 + (ys - y) ** 2 <= margin ** 2
        return bool(np.any(self.__data[x0:x1, y0:y1][within_margin] > 0))

    def update_mask(self, x, y, radius, erase=False):
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
        if abs and self in abs.current_channel_mask:
            entry = (abs, abs.current_channel_mask, self, abs.current_channel_mask.index(self))
            segment.__redo_actions.clear()
            segment.__deleted_stack.append(entry)
            segment.__action_history.append(("delete", entry))
            abs.current_channel_mask.remove(self)
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
        segment.__redo_actions.clear()
        self._undo_stack.append(cur.copy())
        self._redo_stack.clear()
        segment.__action_history.append(("edit", self))

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

    @classmethod
    def _restore_deleted_entry(cls, entry) -> bool:
        if entry not in cls.__deleted_stack:
            return False

        abs_obj, seg_list, seg_obj, index = entry
        cls.__deleted_stack.remove(entry)
        if seg_obj in seg_list:
            return False

        insert_at = max(0, min(index, len(seg_list)))
        seg_list.insert(insert_at, seg_obj)

        try:
            loaded = seg_obj.gui.getStove().getLoaded()
            if loaded is abs_obj and abs_obj.current_channel_mask is seg_list:
                seg_obj.draw = True
                seg_obj.selected = False
        except Exception:
            pass

        return True

    @classmethod
    def _redelete_entry(cls, entry) -> bool:
        abs_obj, seg_list, seg_obj, index = entry
        if seg_obj not in seg_list:
            return False

        seg_list.remove(seg_obj)
        cls.__deleted_stack.append(entry)

        try:
            loaded = seg_obj.gui.getStove().getLoaded()
            if loaded is abs_obj and abs_obj.current_channel_mask is seg_list:
                seg_obj.selected = False
                seg_obj.draw = False
                if cls.getBuffer() is seg_obj:
                    cls.clearBuffer()
        except Exception:
            pass

        return True

    @classmethod
    def undo_latest_action(cls, abs_obj) -> bool:
        if not abs_obj:
            return False

        seg_list = abs_obj.current_channel_mask
        for idx in range(len(cls.__action_history) - 1, -1, -1):
            kind, payload = cls.__action_history[idx]

            if kind == "edit":
                seg_obj = payload
                if seg_obj not in seg_list:
                    continue
                if not seg_obj._undo_stack:
                    del cls.__action_history[idx]
                    continue
                if seg_obj.undo():
                    cls.__redo_actions.append(cls.__action_history.pop(idx))
                    return True

            elif kind == "delete":
                abs_entry, seg_entry, seg_obj, _ = payload
                if abs_entry is not abs_obj or seg_entry is not seg_list:
                    continue
                if cls._restore_deleted_entry(payload):
                    cls.__redo_actions.append(cls.__action_history.pop(idx))
                    return True
                del cls.__action_history[idx]

        return False

    @classmethod
    def redo_latest_action(cls, abs_obj) -> bool:
        if not abs_obj:
            return False

        seg_list = abs_obj.current_channel_mask
        for idx in range(len(cls.__redo_actions) - 1, -1, -1):
            kind, payload = cls.__redo_actions[idx]

            if kind == "edit":
                seg_obj = payload
                if seg_obj not in seg_list:
                    continue
                if not seg_obj._redo_stack:
                    del cls.__redo_actions[idx]
                    continue
                if seg_obj.redo():
                    cls.__action_history.append(cls.__redo_actions.pop(idx))
                    return True

            elif kind == "delete":
                abs_entry, seg_entry, _, _ = payload
                if abs_entry is not abs_obj or seg_entry is not seg_list:
                    continue
                if cls._redelete_entry(payload):
                    cls.__action_history.append(cls.__redo_actions.pop(idx))
                    return True
                del cls.__redo_actions[idx]

        return False

    @classmethod
    def reset_loaded(cls, abs_obj) -> bool:
        if not abs_obj:
            return False

        seg_list = abs_obj.current_channel_mask
        changed = False

        remaining_deleted = []
        to_restore = []
        for entry in cls.__deleted_stack:
            if entry[0] is abs_obj and entry[1] is seg_list:
                to_restore.append(entry)
            else:
                remaining_deleted.append(entry)
        cls.__deleted_stack = remaining_deleted

        while to_restore:
            _, _, seg_obj, index = to_restore.pop()
            if seg_obj in seg_list:
                continue
            insert_at = max(0, min(index, len(seg_list)))
            seg_list.insert(insert_at, seg_obj)
            try:
                seg_obj.draw = True
                seg_obj.selected = False
            except Exception:
                pass
            changed = True

        for seg_obj in list(seg_list):
            seg_obj._ensure_history()
            current = seg_obj._get_mask()
            original = seg_obj._original_mask
            is_changed = (
                current is not None and original is not None and
                not np.array_equal(current, original)
            )
            had_history = bool(seg_obj._undo_stack or seg_obj._redo_stack)

            if is_changed:
                seg_obj._set_mask(original.copy())
                try:
                    seg_obj.recal_patch()
                except Exception:
                    pass
                changed = True

            if had_history:
                changed = True

            seg_obj._undo_stack.clear()
            seg_obj._redo_stack.clear()

        cls.__action_history = [
            action for action in cls.__action_history
            if not (
                (action[0] == "edit" and action[1] in seg_list) or
                (action[0] == "delete" and action[1][0] is abs_obj and action[1][1] is seg_list)
            )
        ]
        cls.__redo_actions = [
            action for action in cls.__redo_actions
            if not (
                (action[0] == "edit" and action[1] in seg_list) or
                (action[0] == "delete" and action[1][0] is abs_obj and action[1][1] is seg_list)
            )
        ]

        return changed
