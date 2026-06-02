from unittest.mock import MagicMock, patch

from fishGUI_multichannel.gui.buttons import funcButton
from fishGUI_multichannel.services.session_manager import SessionManager


def _make_button_handler():
    button = funcButton.__new__(funcButton)
    button.gui = MagicMock()
    button.toggle = {
        "BBOX": MagicMock(),
        "SEGMENT": MagicMock(),
        "SEGMENTATION_SELECTION": MagicMock(),
        "EXPORT": MagicMock(),
    }
    button.APPLY_CHANNEL_MASK = MagicMock()
    return button


def test_select_call_when_turning_off_resets_gallery_and_refocuses_selected_pool():
    button = _make_button_handler()
    first = MagicMock(bbox_generated=True)
    second = MagicMock(bbox_generated=False)
    button.selectButtonPressed = MagicMock(return_value=False)

    with patch.object(SessionManager, "getPool", return_value=[first, second]), \
         patch.object(SessionManager, "removeUnselected") as mock_remove, \
         patch.object(SessionManager, "sendFirst") as mock_send_first:
        button.SELECT_call()

    mock_remove.assert_called_once_with()
    button.gui.getTifSequence.return_value.resetPosition.assert_called_once_with()
    assert first.thumbnail == "bbox"
    assert second.thumbnail == "default"
    mock_send_first.assert_called_once_with()


def test_bbox_call_warns_and_resets_toggle_when_no_image_is_loaded():
    button = _make_button_handler()
    button.gui.getStove.return_value.isLoaded.return_value = False

    button.BBOX_call()

    button.gui.popBox.assert_called_once_with("w", "Image Not Loaded", "Please select an image first")
    button.toggle["BBOX"].set.assert_called_once_with(0)


def test_bbox_call_enables_bbox_overlay_when_ready():
    button = _make_button_handler()
    loaded = MagicMock(bbox_generated=True)
    button.gui.getStove.return_value.isLoaded.return_value = True
    button.bboxButtonPressed = MagicMock(return_value=True)

    with patch.object(SessionManager, "getBuffer", return_value=loaded):
        button.BBOX_call()

    assert loaded.drawBbox is True


def test_segment_selection_call_clears_frame_selection_and_restores_thumbnail_states_when_turning_off():
    button = _make_button_handler()
    segmented = MagicMock(segment_generated=True, bbox_generated=True)
    bbox_only = MagicMock(segment_generated=False, bbox_generated=True)
    plain = MagicMock(segment_generated=False, bbox_generated=False)
    button.segButtonPressed = MagicMock(return_value=False)
    button.frameSegButtonPressed = MagicMock(return_value=False)

    with patch.object(SessionManager, "getPool", return_value=[segmented, bbox_only, plain]):
        button.SEGMENT_SELECTION_call()

    assert segmented.selected_for_segmentation is False
    assert segmented.thumbnail == "segmented"
    assert bbox_only.thumbnail == "bbox"
    assert plain.thumbnail == "default"


def test_segment_call_starts_segmentation_and_shows_selected_overlays_when_enabled():
    button = _make_button_handler()
    selected_frame = MagicMock(selected_for_segmentation=True)
    button.segButtonPressed = MagicMock(return_value=True)

    with patch.object(SessionManager, "getPool", return_value=[selected_frame]), \
         patch.object(SessionManager, "segment_selected") as mock_segment_selected:
        button.SEGMENT_call()

    mock_segment_selected.assert_called_once_with(button.gui)
    assert selected_frame.drawSegmentation is True


def test_apply_channel_mask_call_shows_warning_when_no_channels_are_available():
    button = _make_button_handler()

    with patch.object(SessionManager, "get_all_available_channels", return_value=[]):
        button.APPLY_CHANNEL_MASK_call()

    button.toggle["BBOX"].set.assert_called_once_with(0)
    button.toggle["SEGMENTATION_SELECTION"].set.assert_called_once_with(0)
    button.toggle["SEGMENT"].set.assert_called_once_with(0)
    button.gui.popBox.assert_called_once_with("w", "No Channels", "No available channels found in any frame.")


def test_export_call_warns_and_resets_toggle_when_no_image_is_loaded():
    button = _make_button_handler()
    button.gui.getStove.return_value.isLoaded.return_value = False

    with patch("fishGUI_multichannel.gui.buttons.tkinter.messagebox.showwarning") as mock_warning:
        button.EXPORT_call()

    mock_warning.assert_called_once_with("Image Not Loaded", "Please select an image first")
    button.toggle["EXPORT"].set.assert_called_once_with(0)