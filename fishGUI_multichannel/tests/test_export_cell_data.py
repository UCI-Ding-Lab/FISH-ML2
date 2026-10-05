import pathlib
from unittest.mock import MagicMock

import numpy as np

from fishGUI_multichannel.services.export_cell_data import (
    build_paired_export_data,
    extract_export_channel,
    first_cytoplasm_channel_and_path,
    frame_has_whole_cell_masks,
)


def test_extract_export_channel_reads_a_supported_cytoplasm_channel_from_the_filename():
    """Read a documented cytoplasm channel from an export image path."""
    path = pathlib.Path("img_s001_w647_s001.tif")

    channel = extract_export_channel(path)

    assert channel == "647"


def test_extract_export_channel_reads_an_undocumented_cytoplasm_channel():
    """Read an imported custom channel from an export image path."""
    path = pathlib.Path("img_s001_wCUSTOM_s001.tif")

    channel = extract_export_channel(path)

    assert channel == "CUSTOM"


def test_build_paired_export_data_returns_only_matched_cytoplasm_and_nucleus_masks():
    """Ensure export rebuilds pairing and returns the matched masks."""
    abs_obj = MagicMock()
    cyto_mask = np.array([[1, 0], [0, 1]], dtype=np.uint8)
    nucleus_mask = np.array([[0, 1], [1, 0]], dtype=np.uint8)
    cyto_seg = MagicMock(xy=(3.0, 4.0), box=cyto_mask, _segment__data=cyto_mask.T)
    nucleus_seg = MagicMock(box=nucleus_mask, _segment__data=nucleus_mask.T)
    abs_obj.get_segments.return_value = [cyto_seg]
    abs_obj.get_nucleus_segments.return_value = [nucleus_seg]
    abs_obj.get_pairings.return_value = {"pairs": [{"cytoplasm_index": 0, "nucleus_index": 0}]}

    xy, masks, nucleus_masks = build_paired_export_data(abs_obj, "647")

    abs_obj.update_pairings_for_channel.assert_called_once_with("647")
    assert xy == [(1, 1)]
    assert np.array_equal(masks[0], cyto_mask.astype(bool))
    assert np.array_equal(nucleus_masks[0], nucleus_mask.astype(bool))


def test_first_cytoplasm_channel_and_path_returns_the_first_channel():
    """Use the first cytoplasm channel in the frame's channel order."""
    frame = MagicMock()
    frame.getCytoplasmChannelsAndPaths.return_value = {
        "647": pathlib.Path("s001_w647.tif"),
        "488": pathlib.Path("s001_w488.tif"),
    }

    assert first_cytoplasm_channel_and_path(frame) == ("647", pathlib.Path("s001_w647.tif"))


def test_first_cytoplasm_channel_and_path_is_none_without_cytoplasm_channels():
    """Return None for a DAPI-only frame."""
    frame = MagicMock()
    frame.getCytoplasmChannelsAndPaths.return_value = {}

    assert first_cytoplasm_channel_and_path(frame) is None


def test_frame_has_whole_cell_masks_checks_only_the_first_channel():
    """Report whole-cell masks only when the exported channel has them."""
    frame = MagicMock()
    frame.getCytoplasmChannelsAndPaths.return_value = {"647": pathlib.Path("a.tif"), "488": pathlib.Path("b.tif")}
    frame.has_segments.side_effect = lambda channel: channel == "488"

    assert frame_has_whole_cell_masks(frame) is False
