import threading
from unittest.mock import MagicMock, patch

from fishGUI_multichannel.gui.abstract import abstract
from fishGUI_multichannel.services.session_manager import SessionManager


def _make_bare_abstract():
    abs_obj = abstract.__new__(abstract)
    abs_obj._abstract__bbox_generated = False
    abs_obj._abstract__label = MagicMock()
    abs_obj.getLabel = MagicMock(return_value=abs_obj._abstract__label)
    abs_obj.gui = MagicMock()
    return abs_obj


def _run_in_worker_thread(fn):
    worker = threading.Thread(target=fn)
    worker.start()
    worker.join()


def test_update_thumbnail_from_a_worker_thread_is_moved_to_the_main_thread():
    abs_obj = _make_bare_abstract()

    _run_in_worker_thread(abs_obj.update_thumbnail)

    abs_obj.gui.getRoot.return_value.after.assert_called_once_with(0, abs_obj.update_thumbnail)
    abs_obj.getLabel.return_value.config.assert_not_called()


def test_bbox_generated_from_a_worker_thread_reads_tk_state_only_on_the_main_thread():
    abs_obj = _make_bare_abstract()
    abs_obj.update_thumbnail = MagicMock()
    scheduled = []
    abs_obj.gui.getRoot.return_value.after.side_effect = lambda delay, callback: scheduled.append(callback)
    abs_obj.gui.getFuncButton.return_value.selectButtonPressed.return_value = False

    def mark_generated():
        abs_obj.bbox_generated = True

    _run_in_worker_thread(mark_generated)

    assert abs_obj.bbox_generated is True
    abs_obj.gui.getFuncButton.return_value.selectButtonPressed.assert_not_called()
    abs_obj.update_thumbnail.assert_not_called()

    for callback in scheduled:
        callback()

    abs_obj.update_thumbnail.assert_called_once_with()


def test_segment_each_leaves_the_users_selected_channel_alone():
    gui = MagicMock()
    frame = MagicMock(sample_id=1, available_channels=["647", "488"])
    frame.get_segments.return_value = []
    channel_writes = []
    type(frame).selected_channel = property(lambda self: "647", lambda self, value: channel_writes.append(value))

    SessionManager._segment_each(frame, gui)

    assert channel_writes == []
    assert [c.args[0] for c in frame.segment_channel.call_args_list] == ["647", "488"]


def test_cytoplasm_segmentation_resets_the_selection_toggle_on_the_main_thread():
    gui = MagicMock()
    scheduled = []
    gui.getRoot.return_value.after.side_effect = lambda delay, callback: scheduled.append(callback)
    toggle = gui.getFuncButton.return_value.toggle["SEGMENTATION_SELECTION"]

    class RunNowThread:
        def __init__(self, target=None, daemon=None):
            self.target = target

        def start(self):
            self.target()

    class RunNowExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def submit(self, fn, *args):
            future = MagicMock()
            future.result.return_value = fn(*args)
            return future

    with patch.object(SessionManager, "_get_selected_frames", return_value=[MagicMock(sample_id=1)]), \
         patch.object(SessionManager, "_segment_each"), \
         patch.object(SessionManager, "_export_segmentation_timing_csv"), \
         patch("fishGUI_multichannel.services.session_manager.ThreadPoolExecutor", RunNowExecutor), \
         patch("fishGUI_multichannel.services.session_manager.threading.Thread", RunNowThread):
        SessionManager.segment_selected(gui)

    toggle.set.assert_not_called()
    for callback in scheduled:
        callback()
    toggle.set.assert_called_once_with(0)
