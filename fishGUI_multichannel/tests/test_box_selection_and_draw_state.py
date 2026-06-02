from unittest.mock import MagicMock

from fishGUI_multichannel.gui.canvas.box import box


def _make_bare_box():
    box_obj = box.__new__(box)
    box_obj._box__draw = False
    box_obj._box__selected = False
    box_obj._box__rect = MagicMock()
    box_obj._box__anchors = {
        "bottom-left": MagicMock(),
        "bottom-right": MagicMock(),
        "top-left": MagicMock(),
        "top-right": MagicMock(),
        "pos-anchor": MagicMock(),
    }
    for anchor_obj in box_obj._box__anchors.values():
        anchor_obj.contains.return_value = False
    box_obj.gui = MagicMock()
    box_obj.gui.getStove.return_value.canvas = MagicMock()
    box_obj.gui.getStove.return_value.subplot = MagicMock()
    box_obj.gui.getStove.return_value.subplot.bbox = "subplot-bbox"
    box_obj.gui.getStove.return_value.subplot.patches = []
    return box_obj


def test_draw_true_adds_the_rectangle_patch_and_redraws_the_canvas():
    box_obj = _make_bare_box()

    box_obj.draw = True

    box_obj.gui.getStove.return_value.subplot.add_patch.assert_called_once_with(box_obj.rect)
    box_obj.gui.getStove.return_value.canvas.draw.assert_called_once_with()
    assert box_obj.draw is True


def test_selected_true_updates_edge_color_draws_anchors_and_blits_canvas():
    box_obj = _make_bare_box()
    background = object()
    box_obj.gui.getStove.return_value.canvas.copy_from_bbox.return_value = background

    box_obj.selected = True

    assert box_obj.selected is True
    box_obj.rect.set_edgecolor.assert_called_once_with("cyan")
    for anchor_obj in box_obj.anchors.values():
        assert anchor_obj.draw is True
    box_obj.gui.getStove.return_value.canvas.restore_region.assert_called_once_with(background)
    box_obj.gui.getStove.return_value.subplot.draw_artist.assert_any_call(box_obj.rect)
    assert box_obj.gui.getStove.return_value.subplot.draw_artist.call_count == 1 + len(box_obj.anchors)
    box_obj.gui.getStove.return_value.canvas.blit.assert_called_once_with("subplot-bbox")
    assert box_obj.draw is True


def test_anchor_contains_returns_the_matching_anchor_name_or_none():
    box_obj = _make_bare_box()
    box_obj.anchors["top-right"].contains.return_value = True

    assert box_obj.anchorContains(10, 20) == "top-right"
    box_obj.anchors["top-right"].contains.assert_called_once_with(10, 20)

    for anchor_obj in box_obj.anchors.values():
        anchor_obj.contains.reset_mock()
        anchor_obj.contains.return_value = False

    assert box_obj.anchorContains(1, 2) is None


def test_clear_buffer_and_deselect_unselects_the_buffered_box_and_clears_it():
    box_obj = _make_bare_box()
    box.setBuffer(box_obj)

    box.clearBufferAndDeselect()

    assert box.getBuffer() is None
    assert box_obj.selected is False