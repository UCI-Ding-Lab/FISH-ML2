from fishGUI_multichannel.services.export_modes import (
    BOTH,
    NUCLEUS_ONLY,
    WHOLE_CELL_ONLY,
    guess_export_mode,
)


class FakeFrame:
    """Store which masks one frame has for export mode tests."""

    def __init__(self, nuclei=False, whole_cells=False, selected=True):
        self.selected = selected
        self.nuclei = nuclei
        self.whole_cells = whole_cells

    def has_nucleus_segments(self):
        """Return whether this frame has nucleus masks."""
        return self.nuclei

    def getCytoplasmChannelsAndPaths(self):
        """Return two cytoplasm channels like a real frame."""
        return {"488": "img_w2-488_s001.tif", "647": "img_w3-647_s001.tif"}

    def has_segments(self, channel):
        """Return whether the first cytoplasm channel has whole-cell masks."""
        return self.whole_cells and channel == "488"


def test_guess_is_both_when_frames_have_nuclei_and_whole_cells():
    assert guess_export_mode([FakeFrame(nuclei=True, whole_cells=True)]) == BOTH


def test_guess_is_nucleus_only_when_frames_have_only_nuclei():
    assert guess_export_mode([FakeFrame(nuclei=True)]) == NUCLEUS_ONLY


def test_guess_is_whole_cell_only_when_frames_have_only_whole_cells():
    assert guess_export_mode([FakeFrame(whole_cells=True)]) == WHOLE_CELL_ONLY


def test_guess_is_both_when_nothing_is_segmented():
    assert guess_export_mode([FakeFrame()]) == BOTH


def test_guess_ignores_unselected_frames():
    frames = [FakeFrame(nuclei=True), FakeFrame(whole_cells=True, selected=False)]
    assert guess_export_mode(frames) == NUCLEUS_ONLY


def test_guess_uses_last_mode_when_given():
    frames = [FakeFrame(nuclei=True, whole_cells=True)]
    assert guess_export_mode(frames, last_mode=NUCLEUS_ONLY) == NUCLEUS_ONLY
