import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from fishGUI_multichannel.gui.abstract import abstract


@pytest.fixture
def dummy_paths(tmp_path):
    nucleus = tmp_path / "nucleus.tif"
    cyto1 = tmp_path / "cyto_647.tif"
    cyto2 = tmp_path / "cyto_488.tif"
    return nucleus, [cyto1, cyto2]


def _make_bare_abstract():
    a = abstract.__new__(abstract)
    a._abstract__current_channel = "647"
    a._abstract__current_channel_mask = []
    a._abstract__channel_segments = {ch: [] for ch in abstract.SEGMENT_CHANNELS}
    a._abstract__segment_generated = False
    a._abstract__bbox = []
    a._abstract__bbox_generated = False
    a._abstract__selected = False
    a._abstract__selected_for_segmentation = False
    a._abstract__thumbnail_state = None
    a._abstract__img_tk_thumbnail = object()
    a._abstract__img_tk_thumbnail_bbox = object()
    a._abstract__img_tk_thumbnail_select = object()
    a._abstract__img_tk_thumbnail_crossout = object()
    a._abstract__img_tk_thumbnail_segmented = object()
    a._abstract__img_tk_thumbnail_segmentation_selected = object()
    a._abstract__img_tk_thumbnail_selected_and_segmented = object()
    a._abstract__img_pil_thumbnail = MagicMock()
    a._abstract__img_pil_thumbnail_bbox = MagicMock()
    a._abstract__label = MagicMock()
    a.getLabel = MagicMock(return_value=a._abstract__label)
    a.update_thumbnail = MagicMock()
    a.gui = MagicMock()
    a.gui.getFuncButton.return_value.selectButtonPressed.return_value = False
    a._get_rgb_for_channel = MagicMock(return_value=np.zeros((10, 10, 3), dtype=np.uint8))
    return a


def test_init_and_channels(dummy_paths):
    nucleus, cyto_paths = dummy_paths
    gui = MagicMock()
    gallery_frame = MagicMock()

    with patch("fishGUI_multichannel.gui.abstract.tifffile.imread", return_value=np.zeros((1, 10, 10))), \
         patch("fishGUI_multichannel.gui.abstract.grayscale_to_rgb", return_value=np.zeros((10, 10, 3), dtype=np.uint8)), \
         patch("fishGUI_multichannel.gui.abstract.Image.fromarray"), \
         patch("fishGUI_multichannel.gui.abstract.ImageTk.PhotoImage"), \
         patch("fishGUI_multichannel.gui.abstract.tkinter.Label"), \
         patch("fishGUI_multichannel.gui.abstract.preprocess_nucleus_stack", return_value=np.zeros((10, 10))), \
         patch("fishGUI_multichannel.gui.abstract.preprocess_cytoplasm_stack", return_value=np.zeros((10, 10))), \
         patch("fishGUI_multichannel.gui.abstract.preprocess_cytoplasm_channels", return_value={"647": np.zeros((10, 10)), "488": np.zeros((10, 10))}), \
         patch("fishGUI_multichannel.services.session_manager.SessionManager.addToPool"):
        a = abstract("sample1", nucleus, cyto_paths, gallery_frame, gui)

    assert a.available_channels == ["647", "488"]
    assert a.selected_channel == "647"
    assert a.getNucleusPath() == nucleus
    assert set(a.getCytoplasmPaths()) == set(cyto_paths)


def test_set_and_get_seg_list_for_channel():
    a = _make_bare_abstract()
    a._set_seg_list_for_channel("647", [1, 2, 3])
    assert a._get_seg_list_for_channel("647") == [1, 2, 3]
    assert a._get_seg_list_for_channel("488") == []


def test_get_and_set_segments_api():
    a = _make_bare_abstract()
    a.set_segments("647", [1, 2])
    a.set_segments("488", [3])

    assert a.get_segments() == [1, 2]
    assert a.get_segments("647") == [1, 2]
    assert a.get_segments("488") == [3]
    assert a.has_segments("647") is True
    assert a.has_segments("555") is False
    assert a.has_any_segments() is True


def test_set_mask_for_all_channels():
    a = _make_bare_abstract()
    a.available_channels = ["647", "488"]
    a.set_mask_for_all_channels([42])
    assert a.get_segments("647") == [42]
    assert a.get_segments("488") == [42]


def test_selected_property():
    a = _make_bare_abstract()
    a.selected = True
    assert a.selected is True
    a.selected = False
    assert a.selected is False


def test_selected_for_segmentation_property():
    a = _make_bare_abstract()
    a.selected_for_segmentation = True
    assert a.selected_for_segmentation is True
    a.selected_for_segmentation = False
    assert a.selected_for_segmentation is False


def test_selected_channel_property():
    a = _make_bare_abstract()
    a.set_segments("647", [1])
    a.set_segments("488", [2])
    a.selected_channel = "488"

    assert a.selected_channel == "488"
    assert a.current_channel_mask == [2]
    assert a.seg == [2]


def test_bbox_setter_and_getter():
    a = _make_bare_abstract()
    a.bbox = [1, 2]
    assert a.bbox_generated is True
    assert a.bbox == [1, 2]


def test_segment_generated_property():
    a = _make_bare_abstract()
    a.segment_generated = True
    assert a.segment_generated is True


def test_finalized_mask_setter_and_getter():
    a = _make_bare_abstract()
    a.set_finalized_mask([1, 2, 3])
    assert a.finalized_mask == [1, 2, 3]


def test_seg_property():
    a = _make_bare_abstract()
    a.seg = [3]
    assert a.seg == [3]
    assert a.get_segments("647") == [3]


def test_segment_channel_stores_requested_channel():
    a = _make_bare_abstract()
    a._abstract__bbox_generated = True
    a._abstract__img_np_nucleus = np.zeros((10, 10))
    a._abstract__img_np_647 = np.zeros((10, 10))
    a._abstract__img_np_488 = np.zeros((10, 10))
    a._abstract__img_np_555 = None
    a._abstract__img_np_594 = None
    a._abstract__img_np_514 = None

    with patch("fishGUI_multichannel.gui.abstract.run_cellpose_sam_segmentation", return_value={"488": [99]}) as mock_segment:
        result = a.segment_channel("488")

    assert result == [99]
    assert a.get_segments("488") == [99]
    assert a.get_segments("647") == []
    mock_segment.assert_called_once()


def test_findBoxFromPoint_and_findSegFromPoint():
    a = _make_bare_abstract()

    class Dummy:
        def __init__(self, val):
            self.val = val

        def contains(self, x, y):
            return (x, y) == self.val

    a.bbox = [Dummy((1, 2)), Dummy((3, 4))]
    a.seg = [Dummy((5, 6)), Dummy((7, 8))]

    assert a.findBoxFromPoint(1, 2).val == (1, 2)
    assert a.findBoxFromPoint(9, 9) is None
    assert a.findSegFromPoint(5, 6).val == (5, 6)
    assert a.findSegFromPoint(0, 0) is None


def test_get_nucleus_centers():
    a = _make_bare_abstract()
    a.nucleus_centers = [(1, 2), (3, 4)]
    assert a.getNucleusCenters() == [(1, 2), (3, 4)]
