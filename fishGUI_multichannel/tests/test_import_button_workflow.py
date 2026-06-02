from unittest.mock import MagicMock, patch

from fishGUI_multichannel.gui.buttons import funcButton
from fishGUI_multichannel.services.session_manager import SessionManager


def _make_bare_func_button(gui=None):
    """Create a button handler without building the real Tk widgets."""
    button = funcButton.__new__(funcButton)
    button.gui = gui or MagicMock()
    return button


def test_import_call_exits_without_side_effects_when_folder_selection_is_canceled():
    """Stop early when the user cancels the import folder picker."""
    gui = MagicMock()
    button = _make_bare_func_button(gui)

    with patch("fishGUI_multichannel.gui.buttons.filedialog.askdirectory", return_value=""), \
         patch.object(SessionManager, "generate_bboxes") as mock_generate_bboxes:
        button.IMPORT_call()

    gui.getTifSequence.return_value.addToGallery.assert_not_called()
    mock_generate_bboxes.assert_not_called()
    assert SessionManager.getImportDirectory() is None


def test_import_call_loads_tif_files_sets_import_directory_and_starts_bbox_generation(workspace_temp_dir):
    """Import TIFF files, remember the folder, and trigger bbox generation."""
    folder = workspace_temp_dir / "import_batch"
    folder.mkdir()
    tif_file = folder / "sample_001.tif"
    tif_file.write_bytes(b"")
    (folder / "notes.txt").write_text("ignore me")

    gui = MagicMock()
    gui.getTifSequence.return_value.addToGallery.side_effect = lambda files: SessionManager.addToPool(object())
    button = _make_bare_func_button(gui)

    with patch("fishGUI_multichannel.gui.buttons.filedialog.askdirectory", return_value=str(folder)), \
         patch.object(SessionManager, "generate_bboxes") as mock_generate_bboxes:
        button.IMPORT_call()

    gui.getTifSequence.return_value.addToGallery.assert_called_once_with([tif_file.resolve()])
    assert SessionManager.getImportDirectory() == folder
    mock_generate_bboxes.assert_called_once_with(gui)
