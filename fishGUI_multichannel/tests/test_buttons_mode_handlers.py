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
    """Start cytoplasm frame selection without showing a popup"""
    button = _make_button_handler()
    button.toggle["SEGMENTATION_SELECTION"].get.return_value = 1
    button._exit_nucleus_prompt_mode = MagicMock()

    button.SEGMENT_SELECTION_call()

    button.toggle["SEGMENTATION_SELECTION"].get.assert_called_once_with()
    button._exit_nucleus_prompt_mode.assert_called_once_with()
    button.gui.popBox.assert_not_called()


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


def test_export_call_cancelled_popup_stops_export_and_resets_toggle():
    button = _make_button_handler()
    button.gui.getStove.return_value.isLoaded.return_value = True

    with patch.object(SessionManager, "getPool", return_value=[]),          patch("fishGUI_multichannel.gui.buttons.ask_export_mode", return_value=None),          patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button.EXPORT_call()

    mock_thread.assert_not_called()
    button.gui.indicateWait.assert_not_called()
    button.gui.setLastExportMode.assert_not_called()
    button.toggle["EXPORT"].set.assert_called_once_with(0)


def test_export_call_remembers_and_exports_the_chosen_mode():
    button = _make_button_handler()
    button.gui.getStove.return_value.isLoaded.return_value = True
    button.gui.getLastExportMode.return_value = "nucleus_only"

    with patch.object(SessionManager, "getPool", return_value=[]),          patch("fishGUI_multichannel.gui.buttons.ask_export_mode", return_value="whole_cell_only") as mock_popup,          patch("fishGUI_multichannel.gui.buttons.export_session_to_mat") as mock_export,          patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button.EXPORT_call()
        mock_thread.call_args.kwargs["target"]()

    mock_popup.assert_called_once_with(
        button.gui.getRoot.return_value, "nucleus_only", ["nucleus_only", "whole_cell_only", "both"]
    )
    button.gui.setLastExportMode.assert_called_once_with("whole_cell_only")
    mock_export.assert_called_once_with(button.gui, "whole_cell_only")


def test_nucleus_segmentation_error_popup_shows_the_error_message():
    button = _make_button_handler()
    button._set_nucleus_segment_running = MagicMock()
    failing_frame = MagicMock()
    failing_frame.has_nucleus_segments.return_value = False
    failing_frame.segment_nucleus.side_effect = RuntimeError("model failed")
    scheduled = []
    button.gui.getRoot.return_value.after.side_effect = lambda delay, callback: scheduled.append(callback)

    with patch.object(SessionManager, "getPool", return_value=[failing_frame]), \
         patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button._run_nucleus_segmentation(MagicMock())
        mock_thread.call_args.kwargs["target"]()
    for callback in scheduled:
        callback()

    button.gui.popBox.assert_called_once_with("e", "Nucleus Segmentation Error", "model failed")


def _make_nucleus_frame(has_masks):
    frame = MagicMock()
    frame.has_nucleus_segments.return_value = has_masks
    return frame


def test_nucleus_segmentation_cancel_runs_nothing():
    button = _make_button_handler()
    frames = [_make_nucleus_frame(True), _make_nucleus_frame(False)]

    with patch.object(SessionManager, "getPool", return_value=frames), \
         patch("fishGUI_multichannel.gui.buttons.choose_frames_to_resegment", return_value=None), \
         patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button._run_nucleus_segmentation(MagicMock())

    mock_thread.assert_not_called()
    button.gui.indicateWait.assert_not_called()


def test_nucleus_segmentation_segments_new_frames_and_chosen_frames_without_asking():
    button = _make_button_handler()
    button._set_nucleus_segment_running = MagicMock()
    kept, redone, new = _make_nucleus_frame(True), _make_nucleus_frame(True), _make_nucleus_frame(False)

    with patch.object(SessionManager, "getPool", return_value=[kept, redone, new]), \
         patch("fishGUI_multichannel.gui.buttons.choose_frames_to_resegment", return_value=[redone]) as mock_choose, \
         patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button._run_nucleus_segmentation(MagicMock())
        mock_thread.call_args.kwargs["target"]()

    assert mock_choose.call_args.args[3] == [kept, redone]
    kept.segment_nucleus.assert_not_called()
    redone.segment_nucleus.assert_called_once_with(use_stored_masks=False)
    new.segment_nucleus.assert_called_once_with(use_stored_masks=False)


def test_nucleus_segmentation_with_nothing_to_do_only_redraws():
    button = _make_button_handler()
    focused = MagicMock()

    with patch.object(SessionManager, "getPool", return_value=[_make_nucleus_frame(True)]), \
         patch("fishGUI_multichannel.gui.buttons.choose_frames_to_resegment", return_value=[]), \
         patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button._run_nucleus_segmentation(focused)

    mock_thread.assert_not_called()
    button.gui.getStove.return_value.cook.assert_called_once_with(focused)


def test_cytoplasm_segmentation_cancel_does_not_start():
    button = _make_button_handler()
    button._set_cytoplasm_segment_running = MagicMock()
    frame = MagicMock(selected_for_segmentation=True, available_channels=["488"])

    with patch.object(SessionManager, "getPool", return_value=[frame]), \
         patch("fishGUI_multichannel.gui.buttons.choose_frames_to_resegment", return_value=None), \
         patch.object(SessionManager, "segment_selected") as mock_segment_selected:
        assert button._run_selected_cytoplasm_segmentation() is True

    mock_segment_selected.assert_not_called()
    button._set_cytoplasm_segment_running.assert_not_called()


def test_cytoplasm_segmentation_passes_the_frames_to_resegment():
    button = _make_button_handler()
    button._set_cytoplasm_segment_running = MagicMock()
    with_masks = MagicMock(selected_for_segmentation=True, available_channels=["488", "647"])
    with_masks.get_segments.side_effect = lambda channel: [1] if channel == "488" else []
    without_masks = MagicMock(selected_for_segmentation=True, available_channels=["488"])
    without_masks.get_segments.return_value = []

    with patch.object(SessionManager, "getPool", return_value=[with_masks, without_masks]), \
         patch("fishGUI_multichannel.gui.buttons.choose_frames_to_resegment", return_value=[with_masks]) as mock_choose, \
         patch.object(SessionManager, "segment_selected") as mock_segment_selected:
        button._run_selected_cytoplasm_segmentation()

    assert mock_choose.call_args.args[3] == [with_masks]
    mock_segment_selected.assert_called_once_with(button.gui, [with_masks])
