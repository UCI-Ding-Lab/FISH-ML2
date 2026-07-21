from unittest.mock import MagicMock, patch

from fishGUI_multichannel.gui.buttons import funcButton, get_apply_channel_source_choices
from fishGUI_multichannel.services.session_manager import SessionManager


def _make_button_handler():
    button = funcButton.__new__(funcButton)
    button.gui = MagicMock()
    toggle_names = [
        "SELECT",
        "BBOX",
        "DISPLAY_MASKS",
        "SEGMENTATION_SELECTION",
        "APPLY_CHANNEL_MASK",
        "EXPORT",
    ]
    button.toggle = {name: MagicMock() for name in toggle_names}
    for toggle_var in button.toggle.values():
        toggle_var.get.return_value = 0
    button.gui.getSeasoning.return_value.tools_var = {
        "brush": MagicMock(),
        "eraser": MagicMock(),
        "add_mask": MagicMock(),
    }
    button.APPLY_CHANNEL_MASK = MagicMock()
    return button


def test_select_call_when_turning_off_resets_gallery_and_refocuses_selected_pool():
    button = _make_button_handler()
    first = MagicMock(bbox_generated=True)
    second = MagicMock(bbox_generated=False)

    with patch.object(SessionManager, "getPool", return_value=[first, second]), \
         patch.object(SessionManager, "removeUnselected") as mock_remove, \
         patch.object(SessionManager, "sendFirst") as mock_send_first:
        button.SELECT_call()

    mock_remove.assert_called_once_with()
    button.toggle["SELECT"].get.assert_called_once_with()
    button.gui.getTifSequence.return_value.resetPosition.assert_called_once_with()
    first.update_thumbnail.assert_called_once_with()
    second.update_thumbnail.assert_called_once_with()
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
    button.toggle["BBOX"].get.return_value = 1

    with patch.object(SessionManager, "getBuffer", return_value=loaded):
        button.BBOX_call()

    button.toggle["BBOX"].get.assert_called()
    assert loaded.drawBbox is True


def test_segment_selection_call_clears_frame_selection_and_restores_thumbnail_states_when_turning_off():
    button = _make_button_handler()
    segmented = MagicMock(segment_generated=True, bbox_generated=True)
    bbox_only = MagicMock(segment_generated=False, bbox_generated=True)
    plain = MagicMock(segment_generated=False, bbox_generated=False)

    with patch.object(SessionManager, "getPool", return_value=[segmented, bbox_only, plain]):
        button.SEGMENT_SELECTION_call()

    button.toggle["SEGMENTATION_SELECTION"].get.assert_called_once_with()
    assert segmented.selected_for_segmentation is False
    segmented.update_thumbnail.assert_called_once_with()
    bbox_only.update_thumbnail.assert_called_once_with()
    plain.update_thumbnail.assert_called_once_with()
    button.gui.popBox.assert_called_once_with(
        "i",
        "Select Cytoplasm Frames",
        "Stopped selecting cytoplasm frames.",
    )


def test_segment_selection_call_starts_cytoplasm_frame_selection_when_turning_on():
    """Shows the cytoplasm frame-picking message when selection mode turns on."""
    button = _make_button_handler()
    button.toggle["SEGMENTATION_SELECTION"].get.return_value = 1
    button._exit_nucleus_prompt_mode = MagicMock()

    button.SEGMENT_SELECTION_call()

    button.toggle["SEGMENTATION_SELECTION"].get.assert_called_once_with()
    button._exit_nucleus_prompt_mode.assert_called_once_with()
    button.gui.popBox.assert_called_once_with(
        "i",
        "Select Cytoplasm Frames",
        "Click thumbnails to choose frames for cytoplasm segmentation.",
    )


def test_segment_call_starts_segmentation_for_selected_frames():
    button = _make_button_handler()
    button.gui.getWorkflowMode.return_value = "cytoplasm"
    selected_frame = MagicMock(selected_for_segmentation=True)
    focused = MagicMock()
    button._run_selected_cytoplasm_segmentation = MagicMock(return_value=True)
    button._prepare_cytoplasm_source_channel = MagicMock(return_value=True)

    with patch.object(SessionManager, "getPool", return_value=[selected_frame]), \
         patch.object(SessionManager, "getBuffer", return_value=focused):
        button.SEGMENT_call()

    button._prepare_cytoplasm_source_channel.assert_called_once_with(focused)
    button._run_selected_cytoplasm_segmentation.assert_called_once_with()


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
    button.toggle["DISPLAY_MASKS"].get.return_value = 1

    with patch.object(SessionManager, "getBuffer", return_value=focused):
        button.DISPLAY_MASKS_call()

    assert button.toggle["DISPLAY_MASKS"].get.call_count == 2
    assert focused.drawSegmentation is True


def test_display_masks_call_hides_masks_for_all_frames_when_disabled():
    button = _make_button_handler()
    first = MagicMock()
    second = MagicMock()

    with patch.object(SessionManager, "getBuffer", return_value=first), \
         patch.object(SessionManager, "getPool", return_value=[first, second]):
        button.DISPLAY_MASKS_call()

    assert button.toggle["DISPLAY_MASKS"].get.call_count == 2
    assert first.drawSegmentation is False
    assert second.drawSegmentation is False
    button.gui.getSeasoning.return_value.tools_var["brush"].set.assert_called_once_with(0)
    button.gui.getSeasoning.return_value.tools_var["eraser"].set.assert_called_once_with(0)
    button.gui.getSeasoning.return_value.tools_var["add_mask"].set.assert_called_once_with(0)


def test_apply_channel_mask_call_shows_warning_when_no_channels_are_available():
    button = _make_button_handler()

    with patch.object(SessionManager, "get_all_available_channels", return_value=[]):
        button.APPLY_CHANNEL_MASK_call()

    button.toggle["BBOX"].set.assert_called_once_with(0)
    button.toggle["SEGMENTATION_SELECTION"].set.assert_called_once_with(0)
    button.toggle["DISPLAY_MASKS"].set.assert_called_once_with(0)
    button.gui.getSeasoning.return_value.tools_var["brush"].set.assert_called_once_with(0)
    button.gui.getSeasoning.return_value.tools_var["eraser"].set.assert_called_once_with(0)
    button.gui.getSeasoning.return_value.tools_var["add_mask"].set.assert_called_once_with(0)
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
