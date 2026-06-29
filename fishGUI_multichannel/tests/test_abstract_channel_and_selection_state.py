def test_set_seg_list_for_channel_updates_only_the_requested_channel(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj._set_seg_list_for_channel("647", [1, 2, 3])

    assert abs_obj._get_seg_list_for_channel("647") == [1, 2, 3]
    assert abs_obj._get_seg_list_for_channel("488") == []


def test_segments_api_reads_and_writes_masks_by_channel(bare_abstract_factory):
    """Read and write masks by channel while tracking full segmentation completion."""
    abs_obj = bare_abstract_factory()
    abs_obj.set_segments("647", [1, 2])
    abs_obj.set_segments("488", [3])

    assert abs_obj.get_segments() == [1, 2]
    assert abs_obj.get_segments("647") == [1, 2]
    assert abs_obj.get_segments("488") == [3]
    assert abs_obj.has_segments("647") is True
    assert abs_obj.has_segments("555") is False
    assert abs_obj.has_all_channel_segments() is True


def test_set_mask_for_all_channels_applies_the_same_mask_to_each_available_channel(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj.available_channels = ["647", "488"]
    abs_obj.set_mask_for_all_channels([42])

    assert abs_obj.get_segments("647") == [42]
    assert abs_obj.get_segments("488") == [42]


def test_selected_property_updates_the_frame_selection_state(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj.selected = True
    assert abs_obj.selected is True

    abs_obj.selected = False
    assert abs_obj.selected is False


def test_selected_for_segmentation_property_updates_the_segmentation_selection_state(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj.selected_for_segmentation = True
    assert abs_obj.selected_for_segmentation is True

    abs_obj.selected_for_segmentation = False
    assert abs_obj.selected_for_segmentation is False


def test_selected_channel_property_switches_the_current_channel_mask(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj.set_segments("647", [1])
    abs_obj.set_segments("488", [2])
    abs_obj.selected_channel = "488"

    assert abs_obj.selected_channel == "488"
    assert abs_obj.current_channel_mask == [2]
    assert abs_obj.seg == [2]


def test_bbox_property_marks_bounding_boxes_as_generated_when_assigned(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj.bbox = [1, 2]

    assert abs_obj.bbox_generated is True
    assert abs_obj.bbox == [1, 2]


def test_segment_generated_property_persists_the_generation_flag(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj.segment_generated = True

    assert abs_obj.segment_generated is True


def test_finalized_mask_round_trips_the_assigned_masks(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj.set_finalized_mask([1, 2, 3])

    assert abs_obj.finalized_mask == [1, 2, 3]


def test_seg_property_updates_the_current_channel_mask(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj.seg = [3]

    assert abs_obj.seg == [3]
    assert abs_obj.get_segments("647") == [3]
