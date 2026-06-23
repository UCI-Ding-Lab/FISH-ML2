from unittest.mock import MagicMock

import numpy as np

from fishGUI_multichannel.services.export_pairs import build_paired_export_data, extract_export_channel


def test_extract_export_channel_reads_a_supported_cytoplasm_channel_from_the_filename():
    path = MagicMock()
    path.stem = "sample_647_projection"

    channel = extract_export_channel(path)

    assert channel == "647"


def test_build_paired_export_data_returns_only_matched_cytoplasm_and_nucleus_masks():
    abs_obj = MagicMock()
    cyto_seg = MagicMock(xy=(3.0, 4.0), box=np.array([[1, 0], [0, 1]]))
    nucleus_seg = MagicMock(box=np.array([[0, 1], [1, 0]]))
    abs_obj.get_segments.return_value = [cyto_seg]
    abs_obj.get_nucleus_segments.return_value = [nucleus_seg]
    abs_obj.get_pairings.return_value = {"pairs": [{"cytoplasm_index": 0, "nucleus_index": 0}]}

    xy, masks, nucleus_masks = build_paired_export_data(abs_obj, "647")

    abs_obj.update_pairings_for_channel.assert_not_called()
    assert xy == [(3.0, 4.0)]
    assert np.array_equal(masks[0], cyto_seg.box)
    assert np.array_equal(nucleus_masks[0], nucleus_seg.box)
