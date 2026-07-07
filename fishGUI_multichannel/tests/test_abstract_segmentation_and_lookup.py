import numpy as np
from unittest.mock import MagicMock, patch


def test_segment_channel_stores_results_only_for_the_requested_channel(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj._abstract__bbox_generated = True
    abs_obj._abstract__img_np_nucleus = np.zeros((10, 10))
    abs_obj._abstract__img_np_647 = np.zeros((10, 10))
    abs_obj._abstract__img_np_488 = np.zeros((10, 10))
    abs_obj._abstract__img_np_555 = None
    abs_obj._abstract__img_np_594 = None
    abs_obj._abstract__img_np_514 = None

    with patch("fishGUI_multichannel.gui.abstract.run_cytoplasm_segmentation", return_value={"488": [99]}) as mock_segment:
        result = abs_obj.segment_channel("488")

    assert result == [99]
    assert abs_obj.get_segments("488") == [99]
    assert abs_obj.get_segments("647") == []
    mock_segment.assert_called_once()


def test_segment_nucleus_stores_dapi_masks_separately(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj._abstract__img_np_nucleus = np.zeros((10, 10))

    with patch("fishGUI_multichannel.gui.abstract.run_nucleus_segmentation", return_value=[11, 12]) as mock_segment:
        result = abs_obj.segment_nucleus()

    assert result == [11, 12]
    assert abs_obj.get_nucleus_segments() == [11, 12]
    assert abs_obj.get_segments("647") == []
    mock_segment.assert_called_once_with(
        abs_obj._abstract__img_np_nucleus,
        abs_obj.gui,
        abs_obj.sample_id,
        bbox_list=[],
    )


def test_segment_channel_uses_nucleus_segmentation_when_dapi_is_selected(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj.selected_channel = "DAPI"

    with patch.object(abs_obj, "segment_nucleus", return_value=[31, 32]) as mock_segment_nucleus:
        result = abs_obj.segment_channel()

    assert result == [31, 32]
    mock_segment_nucleus.assert_called_once_with()


def test_bbox_computes_nucleus_centers_once_from_the_nucleus_backend(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj._abstract__img_np_nucleus = np.zeros((10, 10))
    abs_obj.gui.getNucleusBackend.return_value.generate_bboxes.return_value = [(0, 0, 4, 6)]

    result = abs_obj.bbox

    assert result == []
    assert abs_obj.nucleus_centers == [(2.0, 3.0)]
    assert abs_obj.bbox_generated is True


def test_find_methods_return_the_matching_box_and_segment_or_none(bare_abstract_factory):
    abs_obj = bare_abstract_factory()

    class Dummy:
        def __init__(self, val):
            self.val = val

        def contains(self, x, y):
            return (x, y) == self.val

    abs_obj.bbox = [Dummy((1, 2)), Dummy((3, 4))]
    abs_obj.seg = [Dummy((5, 6)), Dummy((7, 8))]

    assert abs_obj.findBoxFromPoint(1, 2).val == (1, 2)
    assert abs_obj.findBoxFromPoint(9, 9) is None
    assert abs_obj.findSegFromPoint(5, 6).val == (5, 6)
    assert abs_obj.findSegFromPoint(0, 0) is None


def test_get_nucleus_centers_returns_the_stored_centers(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    abs_obj.nucleus_centers = [(1, 2), (3, 4)]

    assert abs_obj.getNucleusCenters() == [(1, 2), (3, 4)]


def test_draw_segmentation_uses_dapi_masks_even_when_segment_generated_is_false(bare_abstract_factory):
    abs_obj = bare_abstract_factory()
    dapi_seg = MagicMock()
    abs_obj.set_nucleus_segments([dapi_seg])
    abs_obj.selected_channel = "DAPI"
    abs_obj.segment_generated = False

    abs_obj.drawSegmentation = True

    assert dapi_seg.draw is True
