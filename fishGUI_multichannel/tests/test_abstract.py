import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from fishGUI_multichannel.gui.abstract import abstract

@pytest.fixture
def dummy_paths(tmp_path):
    # Create dummy paths for nucleus and cyto channels
    nucleus = tmp_path / "nucleus.tif"
    cyto1 = tmp_path / "cyto_647.tif"
    cyto2 = tmp_path / "cyto_488.tif"
    # Write dummy files
    np.save(nucleus, np.zeros((10, 10)))
    np.save(cyto1, np.zeros((10, 10)))
    np.save(cyto2, np.zeros((10, 10)))
    return nucleus, [cyto1, cyto2]

@patch("fishGUI_multichannel.gui.abstract.tifffile.imread", return_value=np.zeros((1, 10, 10)))
@patch("fishGUI_multichannel.gui.abstract.grayscale_to_rgb", return_value=np.zeros((10, 10, 3), dtype=np.uint8))
@patch("fishGUI_multichannel.gui.abstract.Image.fromarray")
@patch("fishGUI_multichannel.gui.abstract.preprocess_nucleus_stack", return_value=np.zeros((10, 10)))
@patch("fishGUI_multichannel.gui.abstract.preprocess_cytoplasm_stack", return_value=np.zeros((10, 10)))
@patch("fishGUI_multichannel.gui.abstract.preprocess_cytoplasm_channels", return_value={"647": np.zeros((10, 10)), "488": np.zeros((10, 10))})
def test_init_and_channels(mock_cytoch, mock_cytostack, mock_nucstack, mock_img, mock_rgb, mock_read, dummy_paths):
    nucleus, cyto_paths = dummy_paths
    gui = MagicMock()
    gallery_frame = MagicMock()
    # Patch SessionManager.addToPool to avoid import
    with patch("fishGUI_multichannel.gui.abstract.SessionManager") as sm:
        a = abstract("sample1", nucleus, cyto_paths, gallery_frame, gui)
        assert a.available_channels == ["647", "488"]
        assert a.selected_channel == "647"
        assert a.getNucleusPath() == nucleus
        assert set(a.getCytoplasmPaths()) == set(cyto_paths)

def test_set_and_get_seg_list_for_channel():
    a = abstract.__new__(abstract)
    a._abstract__channel_segments = {}
    a._set_seg_list_for_channel("647", [1, 2, 3])
    assert a._get_seg_list_for_channel("647") == [1, 2, 3]
    assert a._get_seg_list_for_channel("488") == []

def test_set_mask_for_all_channels():
    a = abstract.__new__(abstract)
    a.available_channels = ["647", "488"]
    a._abstract__channel_segments = {}
    a.set_mask_for_all_channels([42])
    assert a._get_seg_list_for_channel("647") == [42]
    assert a._get_seg_list_for_channel("488") == [42]

def test_selected_property():
    a = abstract.__new__(abstract)
    a.thumbnail = None
    a._abstract__selected = False
    a.selected = True
    assert a.selected is True
    a.selected = False
    assert a.selected is False

def test_selected_for_segmentation_property():
    a = abstract.__new__(abstract)
    a._abstract__selected_for_segmentation = False
    a.update_thumbnail = MagicMock()
    a.selected_for_segmentation = True
    assert a.selected_for_segmentation is True
    a.selected_for_segmentation = False
    assert a.selected_for_segmentation is False

def test_selected_channel_property():
    a = abstract.__new__(abstract)
    a.__current_channel = "647"
    a._abstract__current_channel_mask = [1]
    a.current_channel_mask = [2]
    assert a.current_channel_mask == [2]

def test_bbox_setter_and_getter():
    a = abstract.__new__(abstract)
    a.__bbox = []
    a.bbox_generated = False
    a.gui = MagicMock()
    a.gui.getFuncButton.return_value.selectButtonPressed.return_value = False
    a.thumbnail = None
    a.bbox = [1, 2]
    assert a.bbox_generated is True
    assert a.bbox == [1, 2]

def test_segment_generated_property():
    a = abstract.__new__(abstract)
    a._abstract__segment_generated = False
    a.update_thumbnail = MagicMock()
    a.gui = MagicMock()
    a.gui.getFuncButton.return_value.selectButtonPressed.return_value = False
    a.segment_generated = True
    assert a.segment_generated is True

def test_finalized_mask_setter_and_getter():
    a = abstract.__new__(abstract)
    a.set_finalized_mask([1, 2, 3])
    assert a.finalized_mask == [1, 2, 3]

def test_seg_property():
    a = abstract.__new__(abstract)
    a._abstract__current_channel_mask = [1, 2]
    assert a.seg == [1, 2]
    a.seg = [3]
    assert a.seg == [3]

def test_findBoxFromPoint_and_findSegFromPoint():
    a = abstract.__new__(abstract)
    # Dummy box and segment with contains method
    class Dummy:
        def __init__(self, val): self.val = val
        def contains(self, x, y): return (x, y) == self.val
    a.bbox = [Dummy((1, 2)), Dummy((3, 4))]
    a.segment = [Dummy((5, 6)), Dummy((7, 8))]
    assert a.findBoxFromPoint(1, 2).val == (1, 2)
    assert a.findBoxFromPoint(9, 9) is None
    assert a.findSegFromPoint(5, 6).val == (5, 6)
    assert a.findSegFromPoint(0, 0) is None

def test_getNucleusCenters():
    a = abstract.__new__(abstract)
    a.nucleus_centers = [(1, 2), (3, 4)]
    assert a.getNucleusCenters() == [(1, 2), (3, 4)]
