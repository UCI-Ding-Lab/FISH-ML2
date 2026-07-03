import numpy as np

from fishGUI_multichannel.services.export_pairs import build_paired_export_data
from fishGUI_multichannel.services.pairing import finalize_pairing


def test_finalize_pairing_excludes_one_cytoplasm_with_two_nuclei():
    """Ensure one cytoplasm with two nucleus centers inside is excluded from pairs."""
    rows = np.array([0])
    cols = np.array([0])
    meta = {
        (0, 0): (True, 0.9, 0.01),
        (1, 0): (True, 0.8, 0.02),
    }

    result = finalize_pairing(rows, cols, meta, nucleus_count=2, cytoplasm_count=1)

    assert result["pairs"] == []
    assert result["unmatched_nuclei"] == [0, 1]
    assert result["unmatched_cytoplasms"] == [0]


def test_build_paired_export_data_skips_unmatched_nucleus_masks():
    """Ensure export still returns only stored clean pairs."""
    class FakeSegment:
        """Store simple exportable segment values for one test."""

        def __init__(self, xy=None, box=None):
            self.xy = xy
            self.box = box

    class FakeAbstract:
        """Store pairing and segment data used by one export test."""

        def get_pairings(self, channel):
            return {"pairs": [{"cytoplasm_index": 0, "nucleus_index": 0}]}

        def get_segments(self, channel):
            return [FakeSegment(xy=(3.0, 4.0), box=np.array([[1, 0], [0, 1]]))]

        def get_nucleus_segments(self):
            return [
                FakeSegment(box=np.array([[0, 1], [1, 0]])),
                FakeSegment(box=np.array([[1, 1], [0, 0]])),
            ]

    xy, masks, nucleus_masks = build_paired_export_data(FakeAbstract(), "647")

    assert xy == [(3.0, 4.0)]
    assert len(masks) == 1
    assert len(nucleus_masks) == 1
