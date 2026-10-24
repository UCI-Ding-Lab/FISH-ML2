from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from fishGUI_multichannel.services import apply_channel_mask
from fishGUI_multichannel.services.segmentation import (
    describe_failed_frames,
    run_cytoplasm_segmentation,
    run_nucleus_segmentation,
)
from fishGUI_multichannel.services.session_manager import SessionManager


def test_describe_failed_frames_lists_every_failure():
    message = describe_failed_frames("Cytoplasm segmentation", ["3: out of memory", "9: bad image"])

    assert message == "Cytoplasm segmentation failed for 2 frame(s):\n  3: out of memory\n  9: bad image"


def test_nucleus_model_errors_are_raised_instead_of_returning_no_nuclei():
    gui = MagicMock()
    gui.getNucleusBackend.return_value.predict_nucleus.side_effect = RuntimeError("CUDA out of memory")

    with pytest.raises(RuntimeError, match="CUDA out of memory"):
        run_nucleus_segmentation(np.zeros((4, 4)), gui, sample_id=3)


def test_cytoplasm_model_errors_are_raised_instead_of_returning_no_masks():
    gui = MagicMock()
    gui.getCytoplasmBackend.return_value.predict_cytoplasm.side_effect = RuntimeError("CUDA out of memory")
    channels = {"488": np.zeros((4, 4))}

    with pytest.raises(RuntimeError, match="CUDA out of memory"):
        run_cytoplasm_segmentation(np.zeros((4, 4)), channels, gui, "488")


class RunNowThread:
    """Run the thread's job immediately so the test can check what it did."""

    def __init__(self, target=None, daemon=None, name=None):
        self.target = target

    def start(self):
        self.target()


class RunNowExecutor:
    """Run each submitted job immediately and hand back a finished future."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, *args):
        future = MagicMock()
        try:
            value = fn(*args)
            future.result.return_value = value
        except Exception as error:
            future.result.side_effect = error
        return future


def test_cytoplasm_segmentation_reports_failed_frames_and_finishes_the_rest():
    gui = MagicMock()
    scheduled = []
    gui.getRoot.return_value.after.side_effect = lambda delay, callback: scheduled.append(callback)
    good = MagicMock(sample_id=1)
    bad = MagicMock(sample_id=2)
    segmented = []

    def segment_each(frame, gui_arg, resegment):
        if frame is bad:
            raise RuntimeError("CUDA out of memory")
        segmented.append(frame)

    with patch.object(SessionManager, "_get_selected_frames", return_value=[bad, good]), \
         patch.object(SessionManager, "_segment_each", side_effect=segment_each), \
         patch.object(SessionManager, "_export_segmentation_timing_csv") as mock_csv, \
         patch("fishGUI_multichannel.services.session_manager.ThreadPoolExecutor", RunNowExecutor), \
         patch("fishGUI_multichannel.services.session_manager.threading.Thread", RunNowThread):
        SessionManager.segment_selected(gui)
    for callback in scheduled:
        callback()

    assert segmented == [good]
    mock_csv.assert_called_once()
    gui.getFuncButton.return_value._set_cytoplasm_segment_running.assert_called_once_with(False)
    gui.popBox.assert_called_with(
        "e", "Cytoplasm Segmentation Error", "Cytoplasm segmentation failed for 1 frame(s):\n  2: CUDA out of memory"
    )


def test_cytoplasm_segmentation_resets_the_button_even_if_setup_fails():
    gui = MagicMock()
    gui.getRoot.return_value.after.side_effect = lambda delay, callback: callback()

    with patch.object(SessionManager, "_get_selected_frames", return_value=[MagicMock(sample_id=1)]), \
         patch("fishGUI_multichannel.services.session_manager.segmentation_worker_limit", side_effect=RuntimeError("boom")), \
         patch("fishGUI_multichannel.services.session_manager.threading.Thread", RunNowThread):
        with pytest.raises(RuntimeError):
            SessionManager.segment_selected(gui)

    gui.getFuncButton.return_value._set_cytoplasm_segment_running.assert_called_once_with(False)


def test_copy_mask_reports_frames_that_failed():
    good = MagicMock(sample_id="s001", bbox_generated=True, available_channels=["647", "488"])
    bad = MagicMock(sample_id="s002", bbox_generated=True, available_channels=["647", "488"])
    abstract_cls = MagicMock()
    abstract_cls.getPool.return_value = [good, bad]
    abstract_cls.getBuffer.return_value = None

    def ensure(frame, channel):
        if frame is bad:
            raise RuntimeError("CUDA out of memory")

    with patch.object(apply_channel_mask, "ensure_channel_segmented", side_effect=ensure), \
         patch.object(apply_channel_mask, "extract_finalized_masks", return_value=["mask"]), \
         patch.object(apply_channel_mask, "apply_masks_on_main") as mock_apply, \
         patch.object(apply_channel_mask, "update_ui_for_focused_frame"), \
         patch.object(apply_channel_mask, "_get_gui_root", return_value=None), \
         patch.object(apply_channel_mask, "ThreadPoolExecutor", RunNowExecutor), \
         patch.object(apply_channel_mask, "as_completed", side_effect=lambda futures: list(futures)), \
         patch.object(apply_channel_mask.threading, "Thread", RunNowThread), \
         patch.object(apply_channel_mask.messagebox, "showerror") as mock_error:
        apply_channel_mask.apply_channel_mask_to_frames(abstract_cls, "647", [good, bad], ["488"])

    mock_apply.assert_called_once()
    assert mock_apply.call_args.args[0] is good
    mock_error.assert_called_once_with(
        "Copy Mask Error", "Copying the channel mask failed for 1 frame(s):\n  s002: CUDA out of memory"
    )
