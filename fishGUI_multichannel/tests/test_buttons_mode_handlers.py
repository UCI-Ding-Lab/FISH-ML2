from unittest.mock import MagicMock, patch

from fishGUI_multichannel.gui.buttons import funcButton, get_apply_channel_source_choices
from fishGUI_multichannel.services.session_manager import SessionManager


def _make_button_handler():
    button = funcButton.__new__(funcButton)
    button.gui = MagicMock()
    button.toggle = {
        "BBOX": MagicMock(),
        "DISPLAY_MASKS": MagicMock(),
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
    button.frameSegButtonPressed = MagicMock(return_value=False)

    with patch.object(SessionManager, "getPool", return_value=[segmented, bbox_only, plain]):
        button.SEGMENT_SELECTION_call()

    assert segmented.selected_for_segmentation is False
    assert segmented.thumbnail == "segmented"
    assert bbox_only.thumbnail == "bbox"
    assert plain.thumbnail == "default"


def test_segment_selection_call_starts_cytoplasm_frame_selection_when_turning_on():
    """Shows the cytoplasm frame-picking message when selection mode turns on."""
    button = _make_button_handler()
    button.frameSegButtonPressed = MagicMock(return_value=True)
    button._exit_nucleus_prompt_mode = MagicMock()

    button.SEGMENT_SELECTION_call()

    button._exit_nucleus_prompt_mode.assert_called_once_with()
    button.gui.popBox.assert_called_once_with(
        "i",
        "Select Cytoplasm Frames",
        "Control-click thumbnails to choose frames for cytoplasm segmentation.",
    )


def test_segment_call_starts_segmentation_for_selected_frames():
    button = _make_button_handler()
    selected_frame = MagicMock(selected_for_segmentation=True)

    with patch.object(SessionManager, "getPool", return_value=[selected_frame]), \
         patch.object(SessionManager, "segment_selected") as mock_segment_selected:
        button.SEGMENT_call()

    mock_segment_selected.assert_called_once_with(button.gui)


def test_run_cytoplasm_segmentation_uses_selected_frames_when_available():
    """Uses batch segmentation when the user picked cytoplasm frames first."""
    button = _make_button_handler()
    focused = MagicMock()
    button._prepare_cytoplasm_source_channel = MagicMock(return_value=True)
    button._run_selected_cytoplasm_segmentation = MagicMock(return_value=True)

    with patch.object(SessionManager, "getBuffer", return_value=focused):
        button._run_cytoplasm_segmentation()

    button._prepare_cytoplasm_source_channel.assert_called_once_with(focused)
    button._run_selected_cytoplasm_segmentation.assert_called_once_with()
    button.gui.getStove.return_value.cook.assert_not_called()


def test_run_cytoplasm_segmentation_falls_back_to_focused_frame_when_none_selected():
    """Uses the focused frame when no cytoplasm frame selection exists."""
    button = _make_button_handler()
    focused = MagicMock()
    button._prepare_cytoplasm_source_channel = MagicMock(return_value=True)
    button._run_selected_cytoplasm_segmentation = MagicMock(return_value=False)

    with patch.object(SessionManager, "getBuffer", return_value=focused):
        button._run_cytoplasm_segmentation()

    button._prepare_cytoplasm_source_channel.assert_called_once_with(focused)
    button._run_selected_cytoplasm_segmentation.assert_called_once_with()
    button.gui.getStove.return_value.cook.assert_called_once_with(focused)


def test_display_masks_call_shows_masks_for_the_focused_frame_when_enabled():
    button = _make_button_handler()
    focused = MagicMock()
    button.displayMaskButtonPressed = MagicMock(return_value=True)

    with patch.object(SessionManager, "getBuffer", return_value=focused):
        button.DISPLAY_MASKS_call()

    assert focused.drawSegmentation is True


def test_display_masks_call_hides_masks_for_all_frames_when_disabled():
    button = _make_button_handler()
    first = MagicMock()
    second = MagicMock()
    button.displayMaskButtonPressed = MagicMock(return_value=False)

    with patch.object(SessionManager, "getBuffer", return_value=first), \
         patch.object(SessionManager, "getPool", return_value=[first, second]):
        button.DISPLAY_MASKS_call()

    assert first.drawSegmentation is False
    assert second.drawSegmentation is False


def test_apply_channel_mask_call_shows_warning_when_no_channels_are_available():
    button = _make_button_handler()

    with patch.object(SessionManager, "get_all_available_channels", return_value=[]):
        button.APPLY_CHANNEL_MASK_call()

    button.toggle["BBOX"].set.assert_called_once_with(0)
    button.toggle["SEGMENTATION_SELECTION"].set.assert_called_once_with(0)
    button.toggle["DISPLAY_MASKS"].set.assert_called_once_with(0)
    button.gui.popBox.assert_called_once_with("w", "No Channels", "No cytoplasm channels found in any frame.")


def test_get_apply_channel_source_choices_excludes_dapi():
    with patch.object(SessionManager, "get_all_available_channels", return_value=["DAPI", "647", "488"]):
        channels = get_apply_channel_source_choices()

    assert channels == ["647", "488"]


def test_export_call_warns_and_resets_toggle_when_no_image_is_loaded():
    button = _make_button_handler()
    button.gui.getStove.return_value.isLoaded.return_value = False

    with patch("fishGUI_multichannel.gui.buttons.tkinter.messagebox.showwarning") as mock_warning:
        button.EXPORT_call()

    mock_warning.assert_called_once_with("Image Not Loaded", "Please select an image first")
    button.toggle["EXPORT"].set.assert_called_once_with(0)
