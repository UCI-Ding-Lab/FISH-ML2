from unittest.mock import MagicMock, patch

import numpy as np

from fishGUI_multichannel.services.apply_channel_mask import (
    _get_gui_root,
    apply_masks_on_main,
    ensure_channel_segmented,
    extract_finalized_masks,
    filter_cytoplasm_channels,
    is_cytoplasm_channel,
    update_ui_for_focused_frame,
)


class FrameWithSegmentProperty:
    def __init__(self, seg_lists=None, selected_channel="647"):
        self._seg_lists = seg_lists or {}
        self.selected_channel = selected_channel
        self.sample_id = "sample-001"
        self.segment_accesses = 0

    def _get_seg_list_for_channel(self, channel):
        return self._seg_lists.get(channel, [])

    @property
    def segment(self):
        self.segment_accesses += 1
        return ["generated-mask"]


def test_ensure_channel_segmented_generates_missing_channel_masks_and_restores_focus_channel():
    frame = FrameWithSegmentProperty(seg_lists={"647": ["existing"]}, selected_channel="647")

    ensure_channel_segmented(frame, "488")

    assert frame.segment_accesses == 1
    assert frame.selected_channel == "647"


def test_ensure_channel_segmented_skips_generation_when_masks_already_exist():
    frame = FrameWithSegmentProperty(seg_lists={"488": ["existing"]}, selected_channel="647")

    ensure_channel_segmented(frame, "488")

    assert frame.segment_accesses == 0
    assert frame.selected_channel == "647"


def test_extract_finalized_masks_transposes_masks_and_stores_them_on_the_frame():
    frame = MagicMock(sample_id="sample-002")
    seg_a = MagicMock()
    seg_a._segment__data = np.array([[1, 0], [0, 1]])
    seg_b = MagicMock()
    seg_b._segment__data = np.array([[0, 1], [1, 0]])
    frame._get_seg_list_for_channel.return_value = [seg_a, seg_b]

    masks = extract_finalized_masks(frame, "488")

    expected = [seg_a._segment__data.T, seg_b._segment__data.T]
    assert len(masks) == 2
    assert np.array_equal(masks[0], expected[0])
    assert np.array_equal(masks[1], expected[1])
    frame.set_finalized_mask.assert_called_once()


def test_apply_masks_on_main_replaces_target_channel_segments_and_marks_the_frame_generated():
    frame = MagicMock(sample_id="sample-003")
    frame.gui = MagicMock()
    frame.selected_channel = "488"
    old_seg_647 = MagicMock()
    old_seg_488 = MagicMock()
    frame._get_seg_list_for_channel.side_effect = lambda channel: {
        "647": [old_seg_647],
        "488": [old_seg_488],
    }[channel]

    shared_seg_1 = MagicMock()
    shared_seg_2 = MagicMock()
    mask_list = [np.ones((2, 2)), np.zeros((2, 2))]

    with patch("fishGUI_multichannel.services.apply_channel_mask.segment", side_effect=[shared_seg_1, shared_seg_2]):
        apply_masks_on_main(frame, "647", ["647", "488"], mask_list)

    old_seg_647.draw = False
    old_seg_488.draw = False
    frame._set_seg_list_for_channel.assert_any_call("647", [shared_seg_1, shared_seg_2])
    frame._set_seg_list_for_channel.assert_any_call("488", [shared_seg_1, shared_seg_2])
    frame.copy_pairings.assert_called_once_with("647", ["647", "488"])
    frame._get_seg_list_for_channel.assert_any_call("488")
    assert frame.seg == [old_seg_488]
    assert frame.segment_generated is True


def test_is_cytoplasm_channel_returns_false_for_dapi():
    assert is_cytoplasm_channel("647") is True
    assert is_cytoplasm_channel("DAPI") is False


def test_filter_cytoplasm_channels_excludes_dapi():
    channels = filter_cytoplasm_channels(["DAPI", "647", "488"])

    assert channels == ["647", "488"]


def test_update_ui_for_focused_frame_only_enables_segmentation_overlay_for_the_focused_frame():
    frame = MagicMock()
    focused = frame

    update_ui_for_focused_frame(frame, focused, seg_mode_on=True)

    assert frame.drawSegmentation is True

    other_frame = MagicMock()
    update_ui_for_focused_frame(other_frame, focused, seg_mode_on=True)
    assert not hasattr(other_frame, "drawSegmentation") or other_frame.drawSegmentation != True


def test_get_gui_root_prefers_frame_gui_root_and_falls_back_to_abstract_class_root():
    abstract_cls = MagicMock()
    frame = MagicMock()
    frame.gui.getRoot.return_value = "frame-root"

    assert _get_gui_root(abstract_cls, [frame]) == "frame-root"

    abstract_cls.getRoot.return_value = "abstract-root"
    assert _get_gui_root(abstract_cls, []) == "abstract-root"
