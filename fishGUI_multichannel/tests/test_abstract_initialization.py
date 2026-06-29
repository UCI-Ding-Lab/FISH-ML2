import numpy as np
from unittest.mock import MagicMock, patch

from fishGUI_multichannel.gui.abstract import abstract


def test_initialization_exposes_available_channels_and_original_image_paths(dummy_image_paths):
    """Store parsed channel data and the original image paths during setup."""
    nucleus, cyto_paths = dummy_image_paths
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
        abs_obj = abstract("sample1", nucleus, cyto_paths, gallery_frame, gui)

    assert abs_obj.available_channels == ["647", "488"]
    assert abs_obj.selected_channel == "647"
    assert abs_obj.getNucleusPath() == nucleus
    assert set(abs_obj.getCytoplasmPaths()) == set(cyto_paths)
