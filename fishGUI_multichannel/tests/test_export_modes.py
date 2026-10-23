from fishGUI_multichannel.services.export_cell_data import frame_has_any_masks
from fishGUI_multichannel.services.export_modes import (
    BOTH,
    NUCLEUS_ONLY,
    WHOLE_CELL_ONLY,
    available_export_modes,
    export_mode_note,
    guess_export_mode,
)


class FakeFrame:
    """Store which masks one frame has for export mode tests."""

    def __init__(self, nuclei=False, whole_cells=False, selected=True, dapi_only=False, segmented_channel="488"):
        self.selected = selected
        self.nuclei = nuclei
        self.whole_cells = whole_cells
        self.dapi_only = dapi_only
        self.segmented_channel = segmented_channel

    def has_nucleus_segments(self):
        """Return whether this frame has nucleus masks."""
        return self.nuclei

    def getCytoplasmChannelsAndPaths(self):
        """Return two cytoplasm channels like a real frame, or none for a DAPI-only frame."""
        if self.dapi_only:
            return {}
        return {"488": "img_w2-488_s001.tif", "647": "img_w3-647_s001.tif"}

    def has_segments(self, channel):
        """Return whether this cytoplasm channel has whole-cell masks (only the segmented channel does)."""
        return self.whole_cells and channel == self.segmented_channel


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


def test_all_modes_are_available_when_a_frame_has_cytoplasm_images():
    frames = [FakeFrame(dapi_only=True), FakeFrame()]
    assert available_export_modes(frames) == [NUCLEUS_ONLY, WHOLE_CELL_ONLY, BOTH]


def test_only_nucleus_export_is_available_when_only_nuclei_are_segmented():
    frames = [FakeFrame(nuclei=True)]
    assert available_export_modes(frames) == [NUCLEUS_ONLY]


def test_only_whole_cell_export_is_available_when_only_whole_cells_are_segmented():
    frames = [FakeFrame(whole_cells=True)]
    assert available_export_modes(frames) == [WHOLE_CELL_ONLY]


def test_paired_export_is_available_only_when_a_frame_has_both_mask_types():
    frames = [FakeFrame(nuclei=True), FakeFrame(whole_cells=True)]
    assert available_export_modes(frames) == [NUCLEUS_ONLY, WHOLE_CELL_ONLY]
    assert available_export_modes([FakeFrame(nuclei=True, whole_cells=True)]) == [NUCLEUS_ONLY, WHOLE_CELL_ONLY, BOTH]


def test_only_nucleus_only_is_available_when_every_frame_is_dapi_only():
    frames = [FakeFrame(dapi_only=True), FakeFrame(dapi_only=True)]
    assert available_export_modes(frames) == [NUCLEUS_ONLY]


def test_guess_ignores_an_unavailable_last_mode():
    frames = [FakeFrame(nuclei=True, dapi_only=True)]
    assert guess_export_mode(frames, last_mode=BOTH) == NUCLEUS_ONLY


def test_guess_is_nucleus_only_for_unsegmented_dapi_only_frames():
    assert guess_export_mode([FakeFrame(dapi_only=True)]) == NUCLEUS_ONLY


def test_frame_has_any_masks_is_true_with_only_nucleus_masks():
    assert frame_has_any_masks(FakeFrame(nuclei=True))


def test_frame_has_any_masks_is_true_with_whole_cells_in_a_later_channel():
    assert frame_has_any_masks(FakeFrame(whole_cells=True, segmented_channel="647"))


def test_frame_has_any_masks_is_false_when_nothing_is_segmented():
    assert not frame_has_any_masks(FakeFrame())


def test_no_note_when_every_mode_is_available():
    assert export_mode_note([FakeFrame(nuclei=True, whole_cells=True)]) is None


def test_note_mentions_dapi_only_images_when_every_frame_is_dapi_only():
    assert "Only DAPI images are loaded" in export_mode_note([FakeFrame(nuclei=True, dapi_only=True)])


def test_note_mentions_missing_whole_cell_masks_when_cytoplasm_images_are_loaded():
    note = export_mode_note([FakeFrame(nuclei=True)])
    assert "whole-cell masks" in note
    assert "DAPI" not in note


def test_note_mentions_missing_nucleus_masks():
    note = export_mode_note([FakeFrame(whole_cells=True)])
    assert note == "No selected frame has DAPI nucleus masks yet."


def test_note_explains_paired_export_when_no_frame_has_both_mask_types():
    assert "both" in export_mode_note([FakeFrame(nuclei=True), FakeFrame(whole_cells=True)])
