from pathlib import Path
import shutil
from unittest.mock import MagicMock
import uuid

import numpy as np
import pytest

from fishGUI_multichannel.gui.abstract import abstract
from fishGUI_multichannel.services.session_manager import SessionManager


@pytest.fixture(autouse=True)
def reset_session_manager_state():
    SessionManager._SessionManager__pool = []
    SessionManager._SessionManager__buffer = None
    SessionManager._SessionManager__importPath = None
    yield
    SessionManager._SessionManager__pool = []
    SessionManager._SessionManager__buffer = None
    SessionManager._SessionManager__importPath = None


@pytest.fixture
def workspace_temp_dir():
    """Create a writable temporary folder inside the repo for file-based tests."""
    root = Path.cwd() / ".test_temp"
    case_dir = root / str(uuid.uuid4())
    case_dir.mkdir(parents=True, exist_ok=True)
    yield case_dir
    shutil.rmtree(case_dir, ignore_errors=True)


@pytest.fixture
def dummy_image_paths(workspace_temp_dir):
    """Build example image paths that match sample_channels filename parsing."""
    nucleus = workspace_temp_dir / "img_s001_wDAPI_s001.tif"
    cyto1 = workspace_temp_dir / "img_s001_w647_s001.tif"
    cyto2 = workspace_temp_dir / "img_s001_w488_s001.tif"
    cyto_paths = [cyto1, cyto2]
    cyto_channels = ["647", "488"]
    channels = {"DAPI": nucleus, "647": cyto1, "488": cyto2}
    return nucleus, cyto_paths, cyto_channels, channels


@pytest.fixture
def bare_abstract_factory():
    def make_bare_abstract():
        abs_obj = abstract.__new__(abstract)
        abs_obj._abstract__current_channel = "647"
        abs_obj._abstract__cyto_channels = ["647", "488"]
        abs_obj.available_channels = ["647", "488"]
        abs_obj._abstract__img_np_cyto = {
            "647": np.zeros((10, 10)),
            "488": np.zeros((10, 10)),
        }
        abs_obj._abstract__channel_segs = {}
        abs_obj._abstract__segment_generated = False
        abs_obj._abstract__bbox = []
        abs_obj._abstract__bbox_generated = False
        abs_obj._abstract__selected = False
        abs_obj._abstract__selected_for_segmentation = False
        abs_obj._abstract__thumbnail_state = None
        abs_obj._abstract__img_tk_thumbnail = object()
        abs_obj._abstract__img_tk_thumbnail_bbox = object()
        abs_obj._abstract__img_tk_thumbnail_select = object()
        abs_obj._abstract__img_tk_thumbnail_crossout = object()
        abs_obj._abstract__img_tk_thumbnail_segmented = object()
        abs_obj._abstract__img_tk_thumbnail_segmentation_selected = object()
        abs_obj._abstract__img_tk_thumbnail_selected_and_segmented = object()
        abs_obj._abstract__img_pil_thumbnail = MagicMock()
        abs_obj._abstract__img_pil_thumbnail_bbox = MagicMock()
        abs_obj._abstract__label = MagicMock()
        abs_obj.getLabel = MagicMock(return_value=abs_obj._abstract__label)
        abs_obj.update_thumbnail = MagicMock()
        abs_obj.gui = MagicMock()
        abs_obj.gui.getFuncButton.return_value.selectButtonPressed.return_value = False
        abs_obj._get_rgb_for_channel = MagicMock(return_value=np.zeros((10, 10, 3), dtype=np.uint8))
        return abs_obj

    return make_bare_abstract
