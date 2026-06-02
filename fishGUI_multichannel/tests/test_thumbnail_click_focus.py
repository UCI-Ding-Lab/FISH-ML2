from unittest.mock import MagicMock

from fishGUI_multichannel.gui.abstract import abstract
from fishGUI_multichannel.services.session_manager import SessionManager


def _make_bare_abstract(select_mode=False):
    abs_obj = abstract.__new__(abstract)
    abs_obj._abstract__selected = False
    abs_obj._abstract__selected_for_segmentation = False
    abs_obj._abstract__bbox_generated = True
    abs_obj._abstract__drawBbox = False
    abs_obj._abstract__drawSegmentation = False
    abs_obj._abstract__img_tk_thumbnail = object()
    abs_obj._abstract__img_tk_thumbnail_bbox = object()
    abs_obj._abstract__img_tk_thumbnail_select = object()
    abs_obj._abstract__img_tk_thumbnail_crossout = object()
    abs_obj._abstract__img_tk_thumbnail_segmented = object()
    abs_obj._abstract__img_tk_thumbnail_segmentation_selected = object()
    abs_obj._abstract__img_tk_thumbnail_selected_and_segmented = object()
    abs_obj._abstract__img_pil_thumbnail = MagicMock()
    abs_obj._abstract__img_pil_thumbnail_bbox = MagicMock()
    abs_obj._abstract__highlighted = None
    abs_obj._abstract__label = MagicMock()
    abs_obj.getLabel = MagicMock(return_value=abs_obj._abstract__label)
    abs_obj.update_thumbnail = MagicMock()

    gui = MagicMock()
    func_button = gui.getFuncButton.return_value
    func_button.selectButtonPressed.return_value = select_mode
    func_button.bboxButtonPressed.return_value = False
    func_button.segButtonPressed.return_value = False
    gui.getSeasoning.return_value.update_channel_selector_for_image = MagicMock()
    gui.getStove.return_value.bufferSetCurrent = MagicMock()
    gui.getStove.return_value.dump = MagicMock()
    gui.getStove.return_value.cook = MagicMock()
    abs_obj.gui = gui
    return abs_obj


def test_on_click_updates_focus_highlight_and_loads_the_image_into_the_stove():
    prev_abs = _make_bare_abstract()
    current_abs = _make_bare_abstract()
    SessionManager.setBuffer(prev_abs)

    current_abs.on_click(None)

    current_abs.gui.getSeasoning.return_value.update_channel_selector_for_image.assert_called_once_with(current_abs)
    current_abs.gui.getStove.return_value.bufferSetCurrent.assert_called_once_with(3)
    current_abs.gui.getStove.return_value.dump.assert_called_once_with()
    current_abs.gui.getStove.return_value.cook.assert_called_once_with(current_abs)
    assert SessionManager.getBuffer() is current_abs
    prev_abs.getLabel.return_value.config.assert_any_call(borderwidth=0, background="black")
    current_abs.getLabel.return_value.config.assert_any_call(borderwidth=2, background="red")


def test_on_click_in_select_mode_toggles_selection_and_still_loads_the_image():
    current_abs = _make_bare_abstract(select_mode=True)

    current_abs.on_click(None)

    assert current_abs.selected is True
    current_abs.gui.getStove.return_value.cook.assert_called_once_with(current_abs)
    assert SessionManager.getBuffer() is current_abs