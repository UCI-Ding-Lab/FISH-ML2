from unittest.mock import MagicMock

import numpy as np

from fishGUI_multichannel.gui.canvas.segment import segment
from fishGUI_multichannel.gui.canvas.stove import stove


def _make_shift_brush_stove():
    stove_obj = stove.__new__(stove)
    stove_obj.gui = MagicMock()
    stove_obj.canvas = MagicMock()
    stove_obj.subplot = MagicMock()
    stove_obj.subplot.bbox = object()
    stove_obj.subplot.patches = []
    stove_obj.toolbar = MagicMock()
    stove_obj.toolbar.is_tool_active.return_value = False
    stove_obj.xs = []
    stove_obj.ys = []
    stove_obj.markers = []
    stove_obj.press = False
    stove_obj.old_center = None
    stove_obj.creating_new_mask = False
    stove_obj.clearLoaded()
    return stove_obj


def _make_gui_state(stove_obj):
    loaded = MagicMock()
    loaded.current_channel_mask = []
    loaded.getImgNumpyRGB.return_value = np.zeros((6, 8, 3), dtype=np.uint8)
    stove_obj.setLoaded(loaded)

    func_btn = stove_obj.gui.getFuncButton.return_value
    func_btn.bboxButtonPressed.return_value = False
    func_btn.segButtonPressed.return_value = True

    seasoning = stove_obj.gui.getSeasoning.return_value
    seasoning.brushButtonPressed.return_value = True
    seasoning.eraserButtonPressed.return_value = False
    seasoning.get_marker_size.return_value = 1

    tk_widget = stove_obj.canvas.get_tk_widget.return_value
    tk_widget.focus_set = MagicMock()
    stove_obj.canvas.copy_from_bbox.return_value = "bg"
    return loaded


def _make_event(subplot, key="shift", x=2.0, y=3.0):
    event = MagicMock()
    event.button = 1
    event.inaxes = subplot
    event.key = key
    event.xdata = x
    event.ydata = y
    return event


def test_shift_brush_creates_and_paints_a_new_mask():
    stove_obj = _make_shift_brush_stove()
    loaded = _make_gui_state(stove_obj)
    press_event = _make_event(stove_obj.subplot)
    release_event = _make_event(stove_obj.subplot)

    stove_obj.onCanvasClick(press_event)
    stove_obj.onCanvasRelease(release_event)

    assert len(loaded.current_channel_mask) == 1
    assert segment.getBuffer() is loaded.current_channel_mask[0]
    assert np.count_nonzero(loaded.current_channel_mask[0]._get_mask()) > 0
