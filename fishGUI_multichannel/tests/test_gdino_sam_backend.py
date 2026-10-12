import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.fixture
def backend():
    """Build the GroundingDINO + SAM backend with its heavy model module replaced by a stand-in."""
    core_stub = MagicMock()
    with patch.dict(sys.modules, {"core.fishCore_gdino_sam": core_stub}):
        sys.modules.pop("fishGUI_multichannel.backends.gdino_sam_backend", None)
        from fishGUI_multichannel.backends.gdino_sam_backend import GdinoSamBackend

        yield GdinoSamBackend("config.ini", "nucleus")
    sys.modules.pop("fishGUI_multichannel.backends.gdino_sam_backend", None)


@pytest.mark.parametrize("bbox_list", [None, []])
def test_predict_nucleus_returns_no_nuclei_without_boxes(backend, bbox_list):
    masks = backend.predict_nucleus(np.zeros((6, 8)), bbox_list)

    assert masks.shape == (0, 6, 8)
    backend._core.sam_nucleus_predictor.AppIntPREDICTwrapper.assert_not_called()


def test_predict_nucleus_prompts_sam_with_the_frames_boxes(backend):
    boxes = [[0, 0, 4, 4]]

    result = backend.predict_nucleus(np.zeros((6, 8)), boxes)

    predictor = backend._core.sam_nucleus_predictor
    predictor.AppIntPREDICTwrapper.assert_called_once()
    assert predictor.AppIntPREDICTwrapper.call_args.args[1] == boxes
    assert result is predictor.AppIntPREDICTwrapper.return_value
