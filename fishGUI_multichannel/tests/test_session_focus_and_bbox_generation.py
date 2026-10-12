from unittest.mock import MagicMock, patch

from fishGUI_multichannel.gui.abstract import abstract
from fishGUI_multichannel.services.session_manager import SessionManager


def _make_bare_abstract(selected=False):
    abs_obj = abstract.__new__(abstract)
    abs_obj._abstract__selected = selected
    abs_obj.on_click = MagicMock()
    return abs_obj


def test_send_first_focuses_the_first_selected_frame():
    first = _make_bare_abstract(selected=False)
    second = _make_bare_abstract(selected=True)
    third = _make_bare_abstract(selected=True)
    SessionManager._SessionManager__pool = [first, second, third]

    SessionManager.sendFirst()

    first.on_click.assert_not_called()
    second.on_click.assert_called_once_with(None)
    third.on_click.assert_not_called()


def test_generate_bboxes_does_not_start_a_worker_thread_when_the_pool_is_empty():
    gui = MagicMock()

    with patch("fishGUI_multichannel.services.session_manager.threading.Thread") as mock_thread:
        SessionManager.generate_bboxes(gui)

    mock_thread.assert_not_called()


def test_generate_bboxes_submits_each_frame_to_the_background_worker_job():
    gui = MagicMock()
    first = _make_bare_abstract(selected=True)
    second = _make_bare_abstract(selected=True)
    SessionManager._SessionManager__pool = [first, second]

    submitted = []

    class FakeExecutor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, *args):
            submitted.append((fn, args))
            return MagicMock()

    class FakeThread:
        def __init__(self, target=None, daemon=None):
            self.target = target
            self.daemon = daemon

        def start(self):
            self.target()

    with patch("fishGUI_multichannel.services.session_manager.ThreadPoolExecutor", return_value=FakeExecutor()) as mock_executor, \
         patch("fishGUI_multichannel.services.session_manager.threading.Thread", side_effect=FakeThread) as mock_thread, \
         patch("fishGUI_multichannel.services.session_manager.box_generation_worker_limit", return_value=2) as mock_limit, \
         patch.object(SessionManager, "_generate_one_bbox") as mock_generate_one_bbox:
        SessionManager.generate_bboxes(gui)

    mock_limit.assert_called_once_with(2)
    mock_executor.assert_called_once_with(max_workers=2)
    mock_thread.assert_called_once()
    assert mock_thread.call_args.kwargs["daemon"] is True
    assert submitted == [
        (mock_generate_one_bbox, (gui, first)),
        (mock_generate_one_bbox, (gui, second)),
    ]


def test_generate_one_bbox_logs_a_failure_instead_of_hiding_it():
    frame = MagicMock(sample_id=7)
    type(frame).bbox = property(lambda self: (_ for _ in ()).throw(RuntimeError("dino failed")))
    gui = MagicMock()

    with patch("fishGUI_multichannel.services.session_manager.logger") as mock_logger:
        SessionManager._generate_one_bbox(gui, frame)

    mock_logger.exception.assert_called_once_with("Nucleus box generation failed for sample %s", 7)
    gui.getRoot.return_value.after.assert_not_called()
