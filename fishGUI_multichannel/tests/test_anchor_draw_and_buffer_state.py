from unittest.mock import MagicMock

from fishGUI_multichannel.gui.canvas.anchor import anchor


def _make_bare_anchor():
    anchor_obj = anchor.__new__(anchor)
    anchor_obj._anchor__color = "cyan"
    anchor_obj._anchor__draw = False
    anchor_obj._anchor__selected = False
    anchor_obj._anchor__loc = "top-right"
    anchor_obj._anchor__patch = MagicMock()
    anchor_obj.gui = MagicMock()
    anchor_obj.gui.getStove.return_value.subplot = MagicMock()
    anchor_obj.gui.getStove.return_value.subplot.patches = []
    anchor_obj.gui.getStove.return_value.canvas = MagicMock()
    return anchor_obj


def test_draw_true_adds_the_anchor_patch_and_redraws_the_canvas():
    anchor_obj = _make_bare_anchor()

    anchor_obj.draw = True

    anchor_obj.gui.getStove.return_value.subplot.add_patch.assert_called_once_with(anchor_obj.patch)
    anchor_obj.gui.getStove.return_value.canvas.draw.assert_called_once_with()
    assert anchor_obj.draw is True


def test_color_change_updates_patch_edge_color_and_reapplies_draw_state():
    anchor_obj = _make_bare_anchor()

    anchor_obj.color = "b"

    assert anchor_obj.color == "b"
    anchor_obj.patch.set_edgecolor.assert_called_once_with("b")
    anchor_obj.gui.getStove.return_value.canvas.draw.assert_called_once_with()
    assert anchor_obj.draw is True


def test_selected_true_switches_to_blue_and_selected_false_switches_back_to_cyan():
    anchor_obj = _make_bare_anchor()

    anchor_obj.selected = True
    assert anchor_obj.selected is True
    assert anchor_obj.color == "b"

    anchor_obj.selected = False
    assert anchor_obj.selected is False
    assert anchor_obj.color == "cyan"


def test_contains_uses_transformed_data_coordinates():
    anchor_obj = _make_bare_anchor()
    anchor_obj.gui.getStove.return_value.subplot.transData.transform.return_value = (15, 25)
    anchor_obj.patch.contains_point.return_value = True

    result = anchor_obj.contains(1.5, 2.5)

    assert result is True
    anchor_obj.gui.getStove.return_value.subplot.transData.transform.assert_called_once_with((1.5, 2.5))
    anchor_obj.patch.contains_point.assert_called_once_with((15, 25))


def test_clear_buffer_deselects_the_buffered_anchor_and_clears_it():
    anchor_obj = _make_bare_anchor()
    anchor.setBuffer(anchor_obj)

    anchor.clearBuffer()

    assert anchor.getBuffer() is None
    assert anchor_obj.selected is False