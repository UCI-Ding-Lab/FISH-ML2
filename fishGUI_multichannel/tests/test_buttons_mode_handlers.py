from unittest.mock import MagicMock, patch

import pytest

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


def test_run_cytoplasm_segmentation_on_the_focused_frame_shows_model_errors():
    """Shows the error instead of leaving the focused frame without masks silently."""
    button = _make_button_handler()

    class FailingFrame:
        sample_id = 5

        @property
        def segment(self):
            raise RuntimeError("CUDA out of memory")

    focused = FailingFrame()
    button._prepare_cytoplasm_source_channel = MagicMock(return_value=True)
    button._run_selected_cytoplasm_segmentation = MagicMock(return_value=False)

    with patch.object(SessionManager, "getBuffer", return_value=focused):
        button._run_cytoplasm_segmentation()

    button.gui.popBox.assert_called_once_with(
        "e", "Cytoplasm Segmentation Error", "Cytoplasm segmentation failed for 1 frame(s):\n  5: CUDA out of memory"
    )
    button.gui.getStove.return_value.cook.assert_not_called()


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


def test_view_composite_opens_the_composite_window():
    button = _make_button_handler()
    button.composite_window = None

    with patch("fishGUI_multichannel.gui.buttons.compositeWindow") as mock_window:
        button.VIEW_COMPOSITE_call()

    mock_window.assert_called_once_with(button.gui)
    assert button.composite_window is mock_window.return_value


def test_view_composite_brings_an_open_window_to_the_front_instead_of_opening_another():
    button = _make_button_handler()
    open_window = MagicMock()
    open_window.is_open.return_value = True
    button.composite_window = open_window

    with patch("fishGUI_multichannel.gui.buttons.compositeWindow") as mock_window:
        button.VIEW_COMPOSITE_call()

    mock_window.assert_not_called()
    open_window.lift.assert_called_once_with()


def test_view_composite_reopens_after_the_window_was_closed():
    button = _make_button_handler()
    closed_window = MagicMock()
    closed_window.is_open.return_value = False
    button.composite_window = closed_window

    with patch("fishGUI_multichannel.gui.buttons.compositeWindow") as mock_window:
        button.VIEW_COMPOSITE_call()

    mock_window.assert_called_once_with(button.gui)


def _export_frame(selected=True, nuclei=True, whole_cells=False):
    """Build one frame for export tests: selected or not, with or without nucleus and whole-cell masks."""
    frame = MagicMock(selected=selected)
    frame.has_nucleus_segments.return_value = nuclei
    frame.has_segments.return_value = whole_cells
    frame.getCytoplasmChannelsAndPaths.return_value = {"488": "img_w2-488_s001.tif"}
    return frame


def test_export_call_warns_and_stops_when_no_frames_are_selected():
    button = _make_button_handler()
    button.gui.getStove.return_value.isLoaded.return_value = True

    with patch.object(SessionManager, "getPool", return_value=[_export_frame(selected=False)]), \
         patch("fishGUI_multichannel.gui.buttons.tkinter.messagebox.showwarning") as mock_warning, \
         patch("fishGUI_multichannel.gui.buttons.ask_export_mode") as mock_popup, \
         patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button.EXPORT_call()

    assert mock_warning.call_args.args[0] == "No Frames to Export"
    mock_popup.assert_not_called()
    mock_thread.assert_not_called()
    button.toggle["EXPORT"].set.assert_called_once_with(0)


def test_export_call_warns_and_stops_when_nothing_is_segmented():
    button = _make_button_handler()
    button.gui.getStove.return_value.isLoaded.return_value = True

    with patch.object(SessionManager, "getPool", return_value=[_export_frame(nuclei=False)]), \
         patch("fishGUI_multichannel.gui.buttons.tkinter.messagebox.showwarning") as mock_warning, \
         patch("fishGUI_multichannel.gui.buttons.ask_export_mode") as mock_popup, \
         patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button.EXPORT_call()

    assert mock_warning.call_args.args[0] == "Nothing Segmented"
    mock_popup.assert_not_called()
    mock_thread.assert_not_called()
    button.toggle["EXPORT"].set.assert_called_once_with(0)


def test_export_call_cancelled_popup_stops_export_and_resets_toggle():
    button = _make_button_handler()
    button.gui.getStove.return_value.isLoaded.return_value = True

    with patch.object(SessionManager, "getPool", return_value=[_export_frame()]),          patch("fishGUI_multichannel.gui.buttons.ask_export_mode", return_value=None),          patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button.EXPORT_call()

    mock_thread.assert_not_called()
    button.gui.indicateWait.assert_not_called()
    button.gui.setLastExportMode.assert_not_called()
    button.toggle["EXPORT"].set.assert_called_once_with(0)


def test_export_call_remembers_and_exports_the_chosen_mode():
    button = _make_button_handler()
    button.gui.getStove.return_value.isLoaded.return_value = True
    button.gui.getLastExportMode.return_value = "nucleus_only"

    with patch.object(SessionManager, "getPool", return_value=[_export_frame(whole_cells=True)]),          patch("fishGUI_multichannel.gui.buttons.ask_export_mode", return_value="whole_cell_only") as mock_popup,          patch("fishGUI_multichannel.gui.buttons.export_session_to_mat") as mock_export,          patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button.EXPORT_call()
        mock_thread.call_args.kwargs["target"]()

    mock_popup.assert_called_once_with(
        button.gui.getRoot.return_value, "nucleus_only", ["nucleus_only", "whole_cell_only", "both"], None
    )
    button.gui.setLastExportMode.assert_called_once_with("whole_cell_only")
    mock_export.assert_called_once_with(button.gui, "whole_cell_only")


def test_nucleus_segmentation_error_popup_shows_the_error_message():
    button = _make_button_handler()
    button._set_nucleus_segment_running = MagicMock()
    failing_frame = MagicMock(sample_id=4)
    failing_frame.has_nucleus_segments.return_value = False
    failing_frame.compute_nucleus_segments.side_effect = RuntimeError("model failed")
    scheduled = []
    button.gui.getRoot.return_value.after.side_effect = lambda delay, callback: scheduled.append(callback)

    with patch.object(SessionManager, "getPool", return_value=[failing_frame]), \
         patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button._run_nucleus_segmentation(MagicMock())
    mock_thread.call_args.kwargs["target"]()
    for callback in scheduled:
        callback()

    button.gui.popBox.assert_called_once_with(
        "e", "Nucleus Segmentation Error", "Nucleus segmentation failed for 1 frame(s):\n  4: model failed"
    )


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
    scheduled = []
    button.gui.getRoot.return_value.after.side_effect = lambda delay, callback: scheduled.append(callback)

    with patch.object(SessionManager, "getPool", return_value=[kept, redone, new]), \
         patch("fishGUI_multichannel.gui.buttons.choose_frames_to_resegment", return_value=[redone]) as mock_choose, \
         patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button._run_nucleus_segmentation(MagicMock())
    mock_thread.call_args.kwargs["target"]()
    for callback in scheduled:
        callback()

    assert mock_choose.call_args.args[3] == [kept, redone]
    kept.compute_nucleus_segments.assert_not_called()
    kept.set_nucleus_segments.assert_not_called()
    for frame in (redone, new):
        frame.compute_nucleus_segments.assert_called_once_with()
        frame.set_nucleus_segments.assert_called_once_with(frame.compute_nucleus_segments.return_value)
    button.gui.popBox.assert_not_called()


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


def _make_box_frame(sample_id, boxes_ready):
    frame = _make_nucleus_frame(False)
    frame.sample_id = sample_id
    frame.bbox_generated = boxes_ready
    return frame


def _run_nucleus_in_mode(button, mode, frames, generating=False, retry=False):
    button._set_nucleus_segment_running = MagicMock()
    button.gui.getWorkflowMode.return_value = mode
    with patch.object(SessionManager, "getPool", return_value=frames), \
         patch.object(SessionManager, "isGeneratingBboxes", return_value=generating), \
         patch.object(SessionManager, "generate_bboxes") as mock_generate, \
         patch("fishGUI_multichannel.gui.buttons.tkinter.messagebox.askretrycancel", return_value=retry) as mock_retry, \
         patch("fishGUI_multichannel.gui.buttons.choose_frames_to_resegment", return_value=[]) as mock_choose, \
         patch("fishGUI_multichannel.gui.buttons.threading.Thread") as mock_thread:
        button._run_nucleus_segmentation(MagicMock())
    return mock_generate, mock_retry, mock_choose, mock_thread


def test_cellpose_nucleus_segmentation_never_checks_boxes():
    button = _make_button_handler()
    frames = [_make_box_frame(1, boxes_ready=False)]

    _, mock_retry, mock_choose, mock_thread = _run_nucleus_in_mode(button, "nucleus_cellpose", frames)

    mock_choose.assert_called_once()
    mock_thread.assert_called_once()
    mock_retry.assert_not_called()
    button.gui.popBox.assert_not_called()


def test_gdino_nucleus_segmentation_runs_when_every_frame_has_boxes():
    button = _make_button_handler()
    frames = [_make_box_frame(1, True), _make_box_frame(2, True)]

    _, _, mock_choose, mock_thread = _run_nucleus_in_mode(button, "nucleus_gdino", frames)

    mock_choose.assert_called_once()
    mock_thread.assert_called_once()


def test_gdino_nucleus_segmentation_asks_to_wait_while_boxes_are_being_made():
    button = _make_button_handler()
    frames = [_make_box_frame(1, True), _make_box_frame(4, False)]

    mock_generate, mock_retry, mock_choose, mock_thread = _run_nucleus_in_mode(
        button, "nucleus_gdino", frames, generating=True
    )

    title, message = button.gui.popBox.call_args.args[1:]
    assert title == "Nucleus Boxes Not Ready"
    assert "1 frame(s) (4)" in message and "purple dot" in message
    mock_choose.assert_not_called()
    mock_thread.assert_not_called()
    mock_retry.assert_not_called()
    mock_generate.assert_not_called()


@pytest.mark.parametrize("retry", [True, False])
def test_gdino_nucleus_segmentation_offers_retry_when_box_finding_failed(retry):
    button = _make_button_handler()
    missing = _make_box_frame(4, False)
    frames = [_make_box_frame(1, True), missing]

    mock_generate, mock_retry, mock_choose, mock_thread = _run_nucleus_in_mode(
        button, "nucleus_gdino", frames, generating=False, retry=retry
    )

    mock_retry.assert_called_once()
    if retry:
        mock_generate.assert_called_once_with(button.gui, [missing])
    else:
        mock_generate.assert_not_called()
    mock_choose.assert_not_called()
    mock_thread.assert_not_called()


def test_segment_nuclei_in_parallel_uses_the_nucleus_backend_worker_limit():
    button = _make_button_handler()
    frames = [_make_nucleus_frame(False) for _ in range(5)]

    with patch("fishGUI_multichannel.gui.buttons.segmentation_worker_limit", return_value=3) as mock_limit:
        button._segment_nuclei_in_parallel(frames)

    mock_limit.assert_called_once_with(button.gui.getNucleusBackend.return_value, 5)


def test_segment_nuclei_in_parallel_runs_up_to_the_limit_at_the_same_time():
    import threading
    import time

    button = _make_button_handler()
    running = []
    peak = []
    lock = threading.Lock()

    def slow_compute():
        with lock:
            running.append(1)
            peak.append(len(running))
        time.sleep(0.05)
        with lock:
            running.pop()
        return []

    frames = [_make_nucleus_frame(False) for _ in range(6)]
    for frame in frames:
        frame.compute_nucleus_segments.side_effect = slow_compute

    with patch("fishGUI_multichannel.gui.buttons.segmentation_worker_limit", return_value=3):
        button._segment_nuclei_in_parallel(frames)

    assert max(peak) == 3


def test_segment_nuclei_in_parallel_keeps_going_when_one_frame_fails():
    button = _make_button_handler()
    scheduled = []
    button.gui.getRoot.return_value.after.side_effect = lambda delay, callback: scheduled.append(callback)
    good_before, bad, good_after = (_make_nucleus_frame(False) for _ in range(3))
    bad.sample_id = 7
    bad.compute_nucleus_segments.side_effect = RuntimeError("out of memory")

    with patch("fishGUI_multichannel.gui.buttons.segmentation_worker_limit", return_value=3):
        failed = button._segment_nuclei_in_parallel([good_before, bad, good_after])
    for callback in scheduled:
        callback()

    assert failed == ["7: out of memory"]
    good_before.set_nucleus_segments.assert_called_once()
    good_after.set_nucleus_segments.assert_called_once()
    bad.set_nucleus_segments.assert_not_called()
