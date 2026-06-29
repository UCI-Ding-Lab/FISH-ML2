from unittest.mock import MagicMock, call, patch

from fishGUI_multichannel.gui.thumbnails import tifSequence


def _make_bare_tif_sequence(gui=None):
    """Create a lightweight gallery object for focused import tests."""
    sequence = tifSequence.__new__(tifSequence)
    sequence.gui = gui or MagicMock()
    sequence.gallery_frame = MagicMock()
    sequence.update_scrollregion = MagicMock()
    return sequence


def test_add_to_gallery_groups_files_by_sample_and_updates_channel_menu(workspace_temp_dir):
    """Group TIFF files by sample id and refresh the channel menu for each frame."""
    gui = MagicMock()
    sequence = _make_bare_tif_sequence(gui)

    sample1_dapi = workspace_temp_dir / "img_s001_wDAPI.tif"
    sample1_647 = workspace_temp_dir / "img_s001_w647.tif"
    sample1_488 = workspace_temp_dir / "img_s001_w488.tif"
    sample2_dapi = workspace_temp_dir / "img_s002_wDAPI.tif"
    sample2_555 = workspace_temp_dir / "img_s002_w555.tif"

    tif_files = [sample1_647, sample2_555, sample1_dapi, sample2_dapi, sample1_488]

    abstract_1 = MagicMock(available_channels=["647", "488"])
    abstract_2 = MagicMock(available_channels=["555"])

    with patch("fishGUI_multichannel.gui.abstract.abstract", side_effect=[abstract_1, abstract_2]) as mock_abstract, \
         patch("fishGUI_multichannel.gui.thumbnails.SessionManager.sendFirst") as mock_send_first:
        sequence.addToGallery(tif_files)

    assert mock_abstract.call_args_list == [
        call("001", sample1_dapi, [sample1_647, sample1_488], sequence.gallery_frame, gui),
        call("002", sample2_dapi, [sample2_555], sequence.gallery_frame, gui),
    ]
    assert gui.getSeasoning.return_value.update_channel_menu.call_args_list == [
        call(["647", "488"]),
        call(["555"]),
    ]
    mock_send_first.assert_called_once_with()
    sequence.update_scrollregion.assert_called_once_with()


def test_add_to_gallery_skips_samples_that_do_not_have_a_dapi_image(workspace_temp_dir):
    """Skip samples that do not include the required DAPI image."""
    gui = MagicMock()
    sequence = _make_bare_tif_sequence(gui)

    tif_files = [
        workspace_temp_dir / "img_s003_w647.tif",
        workspace_temp_dir / "img_s003_w488.tif",
    ]

    with patch("fishGUI_multichannel.gui.abstract.abstract") as mock_abstract, \
         patch("fishGUI_multichannel.gui.thumbnails.SessionManager.sendFirst") as mock_send_first:
        sequence.addToGallery(tif_files)

    mock_abstract.assert_not_called()
    gui.getSeasoning.return_value.update_channel_menu.assert_not_called()
    mock_send_first.assert_called_once_with()
    sequence.update_scrollregion.assert_called_once_with()
