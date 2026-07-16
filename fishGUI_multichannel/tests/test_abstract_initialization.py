import numpy as np
from unittest.mock import MagicMock, patch

from fishGUI_multichannel.gui.abstract import abstract


def test_initialization_stores_raw_and_display_nucleus_images(dummy_image_paths):
    """Keep both the model-ready nucleus image and the display-ready nucleus image."""
    nucleus, cyto_paths = dummy_image_paths
    gui = MagicMock()
    gallery_frame = MagicMock()
    raw_nucleus = np.arange(100, dtype=np.uint16).reshape(10, 10)
    display_nucleus = np.full((10, 10), 7, dtype=np.uint8)

    with patch("fishGUI_multichannel.gui.abstract.tifffile.imread", return_value=raw_nucleus), \
         patch("fishGUI_multichannel.gui.abstract.grayscale_to_rgb", return_value=np.zeros((10, 10, 3), dtype=np.uint8)), \
         patch("fishGUI_multichannel.gui.abstract.Image.fromarray"), \
         patch("fishGUI_multichannel.gui.abstract.ImageTk.PhotoImage"), \
         patch("fishGUI_multichannel.gui.abstract.tkinter.Label"), \
         patch("fishGUI_multichannel.gui.abstract.normalize_to_uint8", return_value=display_nucleus), \
         patch("fishGUI_multichannel.gui.abstract.preprocess_cytoplasm_stack", return_value=np.zeros((10, 10))), \
         patch("fishGUI_multichannel.gui.abstract.preprocess_cytoplasm_channels", return_value={"647": np.zeros((10, 10)), "488": np.zeros((10, 10))}), \
         patch("fishGUI_multichannel.services.session_manager.SessionManager.addToPool"):
        abs_obj = abstract("sample1", nucleus, cyto_paths, gallery_frame, gui)

    assert abs_obj.available_channels == ["647", "488"]
    assert abs_obj.selected_channel == "647"
    assert abs_obj.getNucleusPath() == nucleus
    assert set(abs_obj.getCytoplasmPaths()) == set(cyto_paths)
    assert np.array_equal(abs_obj._abstract__img_np_nucleus_raw, raw_nucleus)
    assert np.array_equal(abs_obj._abstract__img_np_nucleus, display_nucleus)
