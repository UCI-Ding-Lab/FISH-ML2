from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, PathPatch, Rectangle
from matplotlib.path import Path

from fishGUI_multichannel.gui.composite_window import compositeWindow


def _make_main_stove(frame=None):
    figure = Figure()
    main = MagicMock()
    main.subplot = figure.add_subplot(111)
    main.getLoaded.return_value = frame
    return main


def _make_frame():
    frame = MagicMock()
    frame.getCompositeChannelImages.return_value = {
        "DAPI": np.zeros((16, 16), dtype=np.uint8),
        "647": np.eye(16, dtype=np.uint8) * 255,
    }
    return frame


def _make_bare_window(main_stove):
    window = compositeWindow.__new__(compositeWindow)
    window.stove = main_stove
    window.window = None  # no real Tk window in tests
    window.figure = Figure()
    window.subplot = window.figure.add_subplot(111)
    window.canvas = FigureCanvasAgg(window.figure)
    window.canvas.mpl_connect("draw_event", window.on_own_draw)
    window.channel_vars = {"DAPI": MagicMock(get=lambda: 1), "647": MagicMock(get=lambda: 1)}
    window.chosen_colors = {}
    window.swatches = {"DAPI": MagicMock(), "647": MagicMock()}
    window._rebuild_checkboxes = MagicMock()
    window._setup_view()
    return window


def _mouse_over(axes, x, y):
    return SimpleNamespace(inaxes=axes, xdata=x, ydata=y)


def test_window_shows_the_composite_of_the_main_canvas_frame():
    frame = _make_frame()
    window = _make_bare_window(_make_main_stove(frame))

    window.follow_main_view()

    assert window.shown is frame
    assert window.ax_img.get_array().shape == (16, 16, 3)
    window._rebuild_checkboxes.assert_called_with(["DAPI", "647"])


def test_window_follows_the_main_canvas_zoom_and_pan():
    main_stove = _make_main_stove(_make_frame())
    window = _make_bare_window(main_stove)
    window.follow_main_view()

    main_stove.subplot.set_xlim(2, 6)
    main_stove.subplot.set_ylim(9, 3)
    window.follow_main_view()

    assert window.subplot.get_xlim() == (2, 6)
    assert window.subplot.get_ylim() == (9, 3)


def test_window_never_changes_the_main_canvas_view():
    main_stove = _make_main_stove(_make_frame())
    main_stove.subplot.set_xlim(2, 6)
    window = _make_bare_window(main_stove)
    window.follow_main_view()

    window.subplot.set_xlim(0, 1)
    window.canvas.draw()

    assert main_stove.subplot.get_xlim() == (2, 6)


def test_window_clears_when_the_main_canvas_has_no_frame():
    main_stove = _make_main_stove(_make_frame())
    window = _make_bare_window(main_stove)
    window.follow_main_view()

    main_stove.getLoaded.return_value = None
    window.follow_main_view()

    assert window.shown is None
    assert window.ax_img is None


def test_unticked_channels_are_left_out_of_the_composite():
    window = _make_bare_window(_make_main_stove(_make_frame()))
    window.follow_main_view()

    window.channel_vars["647"] = MagicMock(get=lambda: 0)
    window.on_channel_toggle()

    assert not window.ax_img.get_array().any()


def test_ring_follows_the_mouse_on_the_main_canvas_and_hides_when_it_leaves():
    main_stove = _make_main_stove(_make_frame())
    window = _make_bare_window(main_stove)
    window.follow_main_view()
    window.canvas.draw()

    window.on_main_motion(_mouse_over(main_stove.subplot, 5.0, 7.0))
    assert list(window.cursor.get_xdata()) == [5.0]
    assert list(window.cursor.get_ydata()) == [7.0]

    window.on_main_motion(_mouse_over(None, None, None))
    assert len(window.cursor.get_xdata()) == 0


ASKCOLOR = "fishGUI_multichannel.gui.composite_window.colorchooser.askcolor"


def test_picked_color_is_used_for_that_channel():
    window = _make_bare_window(_make_main_stove(_make_frame()))
    window.follow_main_view()

    with patch(ASKCOLOR, return_value=((0, 255, 255), "#00ffff")):
        window.pick_color("647")

    assert tuple(window.ax_img.get_array()[0, 0]) == (0, 255, 255)
    window.swatches["647"].config.assert_called_once_with(bg="#00ffff")


def test_cancelling_the_color_picker_keeps_the_old_color():
    window = _make_bare_window(_make_main_stove(_make_frame()))
    window.follow_main_view()

    with patch(ASKCOLOR, return_value=(None, None)):
        window.pick_color("647")

    assert tuple(window.ax_img.get_array()[0, 0]) == (255, 0, 0)
    window.swatches["647"].config.assert_not_called()


def test_picked_color_stays_when_switching_frames():
    main_stove = _make_main_stove(_make_frame())
    window = _make_bare_window(main_stove)
    window.follow_main_view()
    with patch(ASKCOLOR, return_value=((0, 255, 255), "#00ffff")):
        window.pick_color("647")

    main_stove.getLoaded.return_value = _make_frame()
    window.follow_main_view()

    assert tuple(window.ax_img.get_array()[0, 0]) == (0, 255, 255)


def _add_main_mask(main_stove, vertices, color="orange"):
    patch = PathPatch(Path(np.array(vertices, dtype=float)), facecolor="none", edgecolor=color, linewidth=0.5)
    main_stove.subplot.add_patch(patch)
    return patch


def _outline_vertices(window):
    return [o.get_path().vertices.tolist() for o in window.outlines]


def test_masks_on_the_main_canvas_appear_as_outlines():
    main_stove = _make_main_stove(_make_frame())
    _add_main_mask(main_stove, [[1, 1], [5, 1], [5, 5]])
    window = _make_bare_window(main_stove)

    window.follow_main_view()

    assert _outline_vertices(window) == [[[1, 1], [5, 1], [5, 5]]]
    assert window.outlines[0].get_facecolor()[3] == 0  # outline only, no fill


def test_boxes_and_circles_on_the_main_canvas_are_not_copied():
    main_stove = _make_main_stove(_make_frame())
    main_stove.subplot.add_patch(Rectangle((0, 0), 4, 4))
    main_stove.subplot.add_patch(Circle((2, 2), 1))
    window = _make_bare_window(main_stove)

    window.follow_main_view()

    assert window.outlines == []


def test_outline_updates_after_a_mask_is_edited():
    main_stove = _make_main_stove(_make_frame())
    mask = _add_main_mask(main_stove, [[1, 1], [5, 1], [5, 5]])
    window = _make_bare_window(main_stove)
    window.follow_main_view()

    mask.get_path().vertices = np.array([[2.0, 2.0], [9.0, 2.0], [9.0, 9.0]])  # what recal_patch does
    window.follow_main_view()

    assert _outline_vertices(window) == [[[2, 2], [9, 2], [9, 9]]]


def test_selected_mask_turns_cyan_in_the_composite_too():
    main_stove = _make_main_stove(_make_frame())
    mask = _add_main_mask(main_stove, [[1, 1], [5, 1], [5, 5]])
    window = _make_bare_window(main_stove)
    window.follow_main_view()

    mask.set_edgecolor("cyan")
    window.follow_main_view()

    assert window.outlines[0].get_edgecolor() == mask.get_edgecolor()


def test_outline_disappears_when_the_mask_is_hidden_or_deleted():
    main_stove = _make_main_stove(_make_frame())
    mask = _add_main_mask(main_stove, [[1, 1], [5, 1], [5, 5]])
    window = _make_bare_window(main_stove)
    window.follow_main_view()

    mask.remove()
    window.follow_main_view()

    assert window.outlines == []
    assert list(window.subplot.patches) == []


def test_copying_outlines_leaves_the_main_canvas_masks_untouched():
    main_stove = _make_main_stove(_make_frame())
    mask = _add_main_mask(main_stove, [[1, 1], [5, 1], [5, 5]])
    window = _make_bare_window(main_stove)
    window.follow_main_view()

    window.outlines[0].get_path().vertices[0] = [99, 99]

    assert list(main_stove.subplot.patches) == [mask]
    assert mask.get_path().vertices[0].tolist() == [1, 1]
