import numpy as np

from fishGUI_multichannel.services.export_cell_data import (
    build_nucleus_only_export_data,
    build_whole_cell_only_export_data,
)


class FakeSegment:
    """Store one full-image mask the way segment objects do."""

    def __init__(self, mask):
        self._segment__data = mask.T


class FakeAbstract:
    """Store nucleus and whole-cell segments for one export test."""

    def __init__(self, nuclei, cells_by_channel):
        self.nuclei = nuclei
        self.cells_by_channel = cells_by_channel

    def get_nucleus_segments(self):
        """Return every nucleus segment."""
        return self.nuclei

    def get_segments(self, channel):
        """Return the whole-cell segments for one channel."""
        return self.cells_by_channel.get(channel, [])


def make_mask(shape, rows, cols):
    """Return a full-image mask with ones in the given row and column slices."""
    mask = np.zeros(shape, dtype=bool)
    mask[rows, cols] = True
    return mask


def test_nucleus_only_export_keeps_every_nucleus_without_pairing():
    nuclei = [
        FakeSegment(make_mask((10, 10), slice(1, 3), slice(2, 5))),
        FakeSegment(make_mask((10, 10), slice(6, 9), slice(6, 8))),
    ]
    abs_obj = FakeAbstract(nuclei, cells_by_channel={})

    xy, masks = build_nucleus_only_export_data(abs_obj)

    assert xy == [(2, 3), (7, 7)]
    assert [mask.shape for mask in masks] == [(2, 3), (3, 2)]
    assert all(mask.all() for mask in masks)


def test_whole_cell_only_export_keeps_every_cell_of_the_channel():
    cells = [FakeSegment(make_mask((10, 10), slice(0, 4), slice(0, 4)))]
    other_channel = [FakeSegment(make_mask((10, 10), slice(5, 6), slice(5, 6)))]
    abs_obj = FakeAbstract(nuclei=[], cells_by_channel={"488": cells, "647": other_channel})

    xy, masks = build_whole_cell_only_export_data(abs_obj, "488")

    assert xy == [(1, 1)]
    assert masks[0].shape == (4, 4)


def test_single_mask_exports_are_empty_without_segments():
    abs_obj = FakeAbstract(nuclei=[], cells_by_channel={})

    assert build_nucleus_only_export_data(abs_obj) == ([], [])
    assert build_whole_cell_only_export_data(abs_obj, "488") == ([], [])
