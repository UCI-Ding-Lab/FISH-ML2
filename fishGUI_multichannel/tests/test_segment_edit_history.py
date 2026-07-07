from unittest.mock import MagicMock

import numpy as np
import pytest

from fishGUI_multichannel.gui.canvas.segment import segment


@pytest.fixture(autouse=True)
def reset_segment_class_state():
    segment._segment__buffer = None
    segment._segment__deleted_stack = []
    segment._segment__action_history = []
    segment._segment__redo_actions = []
    yield
    segment._segment__buffer = None
    segment._segment__deleted_stack = []
    segment._segment__action_history = []
    segment._segment__redo_actions = []


def _make_segment(mask=None):
    gui = MagicMock()
    stove = gui.getStove.return_value
    stove.subplot = MagicMock()
    stove.subplot.patches = []
    stove.canvas = MagicMock()
    stove._batch_segment_draw = False
    stove.getLoaded.return_value = None

    seg = segment(gui, mask if mask is not None else np.array([[1, 0], [0, 0]], dtype=np.uint8))
    seg._segment__patch = MagicMock()
    seg._segment__patch.axes = stove.subplot
    return seg, gui, stove


def test_draw_true_adds_patch_and_redraws_canvas():
    seg, _, stove = _make_segment()

    seg.draw = True

    stove.subplot.add_patch.assert_called_once_with(seg.patch)
    stove.canvas.draw.assert_called_once_with()
    assert seg.draw is True


def test_selected_redraws_only_for_loaded_segment_in_current_channel():
    seg, _, stove = _make_segment()
    loaded = MagicMock()
    loaded.current_channel_mask = [seg]
    stove.getLoaded.return_value = loaded

    seg.selected = True

    assert seg.selected is True
    seg.patch.set_edgecolor.assert_called_once_with("cyan")
    stove.canvas.draw_idle.assert_called_once_with()


def test_delete_removes_segment_from_loaded_mask_records_history_and_flushes_canvas():
    seg, _, stove = _make_segment()
    loaded = MagicMock()
    loaded.current_channel_mask = [seg]
    stove.getLoaded.return_value = loaded
    segment.setBuffer(seg)

    seg.delete()

    assert loaded.current_channel_mask == []
    assert segment.getBuffer() is None
    stove.canvas.flush_events.assert_called_once_with()
    assert len(segment._segment__deleted_stack) == 1
    assert segment._segment__action_history[-1][0] == "delete"


def test_push_undo_undo_and_redo_round_trip_mask_state():
    mask = np.array([[1, 0], [0, 0]], dtype=np.uint8)
    seg, _, _ = _make_segment(mask)
    original = seg._get_mask().copy()

    seg.push_undo()
    seg.update_mask(1, 1, 0, erase=False)
    changed = seg._get_mask().copy()
    assert not np.array_equal(changed, original)

    assert seg.undo() is True
    assert np.array_equal(seg._get_mask(), original)

    assert seg.redo() is True
    assert np.array_equal(seg._get_mask(), changed)


def test_undo_latest_action_restores_last_deleted_segment():
    seg, _, stove = _make_segment()
    loaded = MagicMock()
    loaded.current_channel_mask = [seg]
    stove.getLoaded.return_value = loaded

    seg.delete()

    assert segment.undo_latest_action(loaded) is True
    assert loaded.current_channel_mask == [seg]


def test_reset_loaded_restores_deleted_segments_and_original_masks():
    seg, _, stove = _make_segment(np.array([[1, 0], [0, 0]], dtype=np.uint8))
    loaded = MagicMock()
    loaded.current_channel_mask = [seg]
    stove.getLoaded.return_value = loaded

    seg.push_undo()
    seg.update_mask(1, 1, 0, erase=False)
    deleted, _, _ = _make_segment()
    deleted.gui.getStove.return_value = stove
    segment._segment__deleted_stack.append((loaded, loaded.current_channel_mask, deleted, 1))

    changed = segment.reset_loaded(loaded)

    assert changed is True
    assert deleted in loaded.current_channel_mask
    assert np.array_equal(seg._get_mask(), seg._original_mask)
    assert seg._undo_stack == []
    assert seg._redo_stack == []


def test_create_empty_mask_matches_loaded_image_size():
    seg, gui, _ = _make_segment()

    new_seg = segment.create_empty_mask(gui, (5, 7, 3))

    assert new_seg is not seg
    assert new_seg._get_mask().shape == (5, 7)
    assert np.count_nonzero(new_seg._get_mask()) == 0
