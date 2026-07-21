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
    """Ensure export still returns only rebuilt clean pairs."""
    class FakeSegment:
        """Store simple exportable segment values for one test."""

        def __init__(self, xy=None, box=None):
            self.xy = xy
            self.box = box
            self._segment__data = box.T

    class FakeAbstract:
        """Store pairing and segment data used by one export test."""

        def update_pairings_for_channel(self, channel):
            """Refresh pairing before export for the requested channel."""

        def get_pairings(self, channel):
            """Return one clean pair for the requested channel."""
            return {"pairs": [{"cytoplasm_index": 0, "nucleus_index": 0}]}

        def get_segments(self, channel):
            """Return one cytoplasm segment for the requested channel."""
            return [FakeSegment(xy=(3.0, 4.0), box=np.array([[1, 0], [0, 1]]))]

        def get_nucleus_segments(self):
            """Return two nucleus segments for this export test."""
            return [
                FakeSegment(box=np.array([[0, 1], [1, 0]])),
                FakeSegment(box=np.array([[1, 1], [0, 0]])),
            ]

    xy, masks, nucleus_masks = build_paired_export_data(FakeAbstract(), "647")

    assert xy == [(1, 1)]
    assert len(masks) == 1
    assert len(nucleus_masks) == 1


def test_build_paired_export_data_skips_stale_pair_indexes():
    """Ensure export skips stale pair indexes instead of crashing."""
    class FakeSegment:
        """Store simple exportable segment values for one test."""

        def __init__(self, xy=None, box=None):
            self.xy = xy
            self.box = box
            self._segment__data = box.T

    class FakeAbstract:
        """Store stale pairing data used by one export test."""

        def update_pairings_for_channel(self, channel):
            """Leave the stale pair in place for this safety test."""

        def get_pairings(self, channel):
            """Return one stale pair whose indexes are too large."""
            return {"pairs": [{"cytoplasm_index": 2, "nucleus_index": 3}]}

        def get_segments(self, channel):
            """Return one cytoplasm segment for the requested channel."""
            return [FakeSegment(xy=(3.0, 4.0), box=np.array([[1, 0], [0, 1]]))]

        def get_nucleus_segments(self):
            """Return one nucleus segment for this export test."""
            return [FakeSegment(box=np.array([[0, 1], [1, 0]]))]

    xy, masks, nucleus_masks = build_paired_export_data(FakeAbstract(), "647")

    assert xy == []
    assert masks == []
    assert nucleus_masks == []
