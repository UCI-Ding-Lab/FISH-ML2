from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from fishGUI_multichannel.services import mat_export
from fishGUI_multichannel.services.export_modes import BOTH, NUCLEUS_ONLY, WHOLE_CELL_ONLY
from fishGUI_multichannel.services.session_manager import SessionManager


def make_export_frame(sample_id, channels, selected=True, has_masks=True):
    """Build a sample with ordered image channels without loading real images"""
    frame = MagicMock(selected=selected)
    frame.getCytoplasmChannelsAndPaths.return_value = {
        channel: Path(f"{sample_id}_w{channel}.tif") for channel in channels
    }
    frame.has_segments.return_value = has_masks
    frame.has_nucleus_segments.return_value = has_masks
    return frame


@pytest.fixture
def export_spies():
    """Capture exported data while replacing dialogs and file writing"""
    with (
        patch.object(mat_export.filedialog, "asksaveasfilename", return_value="result.mat"),
        patch.object(mat_export, "write_tracked_mat_file") as writer,
        patch.object(mat_export, "build_paired_export_data", return_value=([(1, 1)], ["cell"], ["nucleus"])) as pairing,
    ):
        yield writer, pairing


def export_frames(frames, export_mode=BOTH, debug_pdf=False):
    """Run the export action on sample doubles with optional PDF output disabled by default"""
    gui = MagicMock()
    gui.shouldExportPairingDebugPdf.return_value = debug_pdf
    with patch.object(SessionManager, "getPool", return_value=frames):
        mat_export.export_session_to_mat(gui, export_mode)


@pytest.mark.parametrize("channels", [("647", "488"), ("488", "647")])
def test_export_uses_first_channel_for_each_sample(channels, export_spies):
    """Export one paired entry per sample using channel order rather than selection"""
    writer, pairing = export_spies
    frames = [make_export_frame(sample, channels) for sample in ("s001", "s002")]
    for frame in frames:
        frame.selected_channel = channels[1]
    export_frames(frames)
    assert pairing.call_args_list == [call(frame, channels[0]) for frame in frames]
    names = [f"{sample}_w{channels[0]}.tif" for sample in ("s001", "s002")]
    writer.assert_called_once_with(names, [[(1, 1)]] * 2, [["cell"]] * 2, [["nucleus"]] * 2, "result.mat", dirname=".")


def test_export_skips_samples_without_cytoplasm_channels(export_spies):
    """Skip a DAPI-only sample while exporting the next sample normally"""
    writer, pairing = export_spies
    dapi_only = make_export_frame("s001", [])
    sample = make_export_frame("s002", ["647"])
    export_frames([dapi_only, sample])
    pairing.assert_called_once_with(sample, "647")
    writer.assert_called_once_with(["s002_w647.tif"], [[(1, 1)]], [["cell"]], [["nucleus"]], "result.mat", dirname=".")


@pytest.mark.parametrize("selected, has_masks", [(False, True), (True, False), (False, False)])
def test_export_keeps_empty_entry_for_unselected_or_unsegmented_sample(selected, has_masks, export_spies):
    """Keep the first channel filename but omit masks when a sample is not ready"""
    writer, pairing = export_spies
    sample = make_export_frame("s001", ["647", "488"], selected, has_masks)
    export_frames([sample])
    pairing.assert_not_called()
    sample.getImgNumpyRGBForChannel.assert_not_called()
    writer.assert_called_once_with(["s001_w647.tif"], [[]], [[]], [[]], "result.mat", dirname=".")


@pytest.fixture
def single_mode_spies(export_spies):
    """Also capture the nucleus-only, whole-cell-only, and debug PDF calls"""
    writer, pairing = export_spies
    with (
        patch.object(mat_export, "build_nucleus_only_export_data", return_value=([(2, 2)], ["nucleus cell"])) as nucleus_only,
        patch.object(mat_export, "build_whole_cell_only_export_data", return_value=([(3, 3)], ["whole cell"])) as whole_cell_only,
        patch.object(mat_export, "export_pairing_debug_pdf", return_value=None) as debug_pdf,
    ):
        yield writer, pairing, nucleus_only, whole_cell_only, debug_pdf


def test_nucleus_only_export_writes_nuclei_without_nucleus_mask_field(single_mode_spies):
    """Export every nucleus in mask and leave out nucleus_mask"""
    writer, pairing, nucleus_only, whole_cell_only, debug_pdf = single_mode_spies
    sample = make_export_frame("s001", ["647"], has_masks=False)
    sample.has_nucleus_segments.return_value = True
    export_frames([sample], NUCLEUS_ONLY, debug_pdf=True)
    nucleus_only.assert_called_once_with(sample)
    pairing.assert_not_called()
    whole_cell_only.assert_not_called()
    debug_pdf.assert_not_called()
    writer.assert_called_once_with(["s001_w647.tif"], [[(2, 2)]], [["nucleus cell"]], None, "result.mat", dirname=".")


def test_whole_cell_only_export_writes_whole_cells_without_nucleus_mask_field(single_mode_spies):
    """Export every whole-cell mask of the first channel and leave out nucleus_mask"""
    writer, pairing, nucleus_only, whole_cell_only, debug_pdf = single_mode_spies
    sample = make_export_frame("s001", ["647", "488"])
    export_frames([sample], WHOLE_CELL_ONLY, debug_pdf=True)
    whole_cell_only.assert_called_once_with(sample, "647")
    pairing.assert_not_called()
    nucleus_only.assert_not_called()
    debug_pdf.assert_not_called()
    writer.assert_called_once_with(["s001_w647.tif"], [[(3, 3)]], [["whole cell"]], None, "result.mat", dirname=".")


def test_nucleus_only_export_keeps_empty_entry_without_nuclei(single_mode_spies):
    """Keep the filename but export no cells when a frame has no nucleus masks"""
    writer, pairing, nucleus_only, whole_cell_only, debug_pdf = single_mode_spies
    sample = make_export_frame("s001", ["647"])
    sample.has_nucleus_segments.return_value = False
    export_frames([sample], NUCLEUS_ONLY)
    nucleus_only.assert_not_called()
    writer.assert_called_once_with(["s001_w647.tif"], [[]], [[]], None, "result.mat", dirname=".")


def test_paired_export_still_writes_debug_pdf_when_requested(single_mode_spies):
    """Only the paired mode writes the pairing debug PDF"""
    writer, pairing, nucleus_only, whole_cell_only, debug_pdf = single_mode_spies
    sample = make_export_frame("s001", ["647"])
    export_frames([sample], BOTH, debug_pdf=True)
    pairing.assert_called_once_with(sample, "647")
    debug_pdf.assert_called_once()


def make_dapi_only_frame(sample_id, selected=True, has_nuclei=True):
    """Build a sample with a DAPI image but no cytoplasm channel images"""
    frame = make_export_frame(sample_id, [], selected=selected)
    frame.getNucleusPath.return_value = Path(f"{sample_id}_wDAPI.tif")
    frame.has_nucleus_segments.return_value = has_nuclei
    return frame


def test_nucleus_only_export_includes_dapi_only_frames_when_all_are_dapi_only(single_mode_spies):
    """Use the DAPI filename when every selected frame is DAPI-only"""
    writer, pairing, nucleus_only, whole_cell_only, debug_pdf = single_mode_spies
    frames = [make_dapi_only_frame("s001"), make_dapi_only_frame("s002")]
    export_frames(frames, NUCLEUS_ONLY)
    assert nucleus_only.call_args_list == [call(frame) for frame in frames]
    writer.assert_called_once_with(
        ["s001_wDAPI.tif", "s002_wDAPI.tif"], [[(2, 2)]] * 2, [["nucleus cell"]] * 2, None, "result.mat", dirname="."
    )


def test_nucleus_only_export_leaves_out_dapi_only_frames_in_mixed_sessions(single_mode_spies):
    """Skip DAPI-only frames when another selected frame has cytoplasm images"""
    writer, pairing, nucleus_only, whole_cell_only, debug_pdf = single_mode_spies
    dapi_only = make_dapi_only_frame("s001")
    sample = make_export_frame("s002", ["647"])
    sample.has_nucleus_segments.return_value = True
    export_frames([dapi_only, sample], NUCLEUS_ONLY)
    nucleus_only.assert_called_once_with(sample)
    writer.assert_called_once_with(["s002_w647.tif"], [[(2, 2)]], [["nucleus cell"]], None, "result.mat", dirname=".")


@pytest.mark.parametrize("export_mode", [WHOLE_CELL_ONLY, BOTH])
def test_whole_cell_modes_still_skip_dapi_only_frames(export_mode, single_mode_spies):
    """Never export DAPI-only frames in modes that need cytoplasm images"""
    writer, pairing, nucleus_only, whole_cell_only, debug_pdf = single_mode_spies
    export_frames([make_dapi_only_frame("s001")], export_mode)
    writer.assert_called_once_with([], [], [], [] if export_mode == BOTH else None, "result.mat", dirname=".")


def export_frames_and_get_warning(frames, export_mode):
    """Run the export and return the warning text passed to the completion popup"""
    with patch.object(mat_export, "show_export_complete") as show_complete:
        export_frames(frames, export_mode)
    return show_complete.call_args.args[2]


def test_no_warning_when_every_selected_frame_has_cells(single_mode_spies):
    """Show the plain completion message when nothing is missing"""
    sample = make_export_frame("s001", ["647"])
    assert export_frames_and_get_warning([sample], BOTH) is None


def test_warning_lists_selected_frames_exported_with_zero_cells(single_mode_spies):
    """List selected frames that had no masks for the chosen mode, but not unselected ones"""
    ready = make_export_frame("s001", ["647"])
    unsegmented = make_export_frame("s002", ["647"], has_masks=False)
    unselected = make_export_frame("s003", ["647"], selected=False, has_masks=False)
    warning = export_frames_and_get_warning([ready, unsegmented, unselected], WHOLE_CELL_ONLY)
    assert "1 selected frame(s) were exported with 0 cells (no masks for Whole-cell only)" in warning
    assert "s002_w647.tif" in warning
    assert "s003_w647.tif" not in warning


def test_warning_lists_dapi_only_frames_left_out_of_mixed_nucleus_only_export(single_mode_spies):
    """Explain that DAPI-only frames were left out because other frames have cytoplasm images"""
    sample = make_export_frame("s001", ["647"])
    sample.has_nucleus_segments.return_value = True
    warning = export_frames_and_get_warning([sample, make_dapi_only_frame("s002")], NUCLEUS_ONLY)
    assert "1 DAPI-only frame(s) were left out because other selected frames have cytoplasm images" in warning
    assert "s002_wDAPI.tif" in warning


def test_warning_explains_dapi_only_frames_left_out_of_whole_cell_modes(single_mode_spies):
    """Explain that whole-cell modes need cytoplasm images"""
    sample = make_export_frame("s001", ["647"])
    warning = export_frames_and_get_warning([sample, make_dapi_only_frame("s002")], BOTH)
    assert "left out because Both (paired) needs cytoplasm images" in warning


def test_format_frame_names_shortens_long_lists():
    """Show at most ten names and count the rest"""
    text = mat_export.format_frame_names([f"s{i:03d}.tif" for i in range(12)])
    assert text.count("\n") == 10
    assert text.endswith("... and 2 more")


@pytest.mark.parametrize("warning, popup", [(None, "showinfo"), ("2 frames missing", "showwarning")])
def test_show_export_complete_uses_a_warning_popup_only_when_needed(warning, popup):
    """Use one popup: information normally, a warning when frames are missing"""
    gui = MagicMock()
    with patch.object(mat_export.messagebox, "showinfo") as showinfo, \
         patch.object(mat_export.messagebox, "showwarning") as showwarning:
        mat_export.show_export_complete(gui, "summary", warning)
        gui.getRoot.return_value.after.call_args.args[1]()
    used = {"showinfo": showinfo, "showwarning": showwarning}
    used[popup].assert_called_once()
    other = "showwarning" if popup == "showinfo" else "showinfo"
    used[other].assert_not_called()


def test_describe_left_out_says_nothing_was_left_out():
    text = mat_export.describe_left_out({"cells": 0, "nuclei": 0}, debug_pdf_written=False)
    assert text == "Left out (no partner): 0 whole-cell masks and 0 nucleus masks"


def test_describe_left_out_points_to_the_pdf_flag_when_no_pdf_was_written():
    text = mat_export.describe_left_out({"cells": 12, "nuclei": 1}, debug_pdf_written=False)
    assert text.startswith("Left out (no partner): 12 whole-cell masks and 1 nucleus mask\n")
    assert "--export-pairing-debug-pdf" in text


def test_describe_left_out_points_to_the_pdf_when_it_was_written():
    text = mat_export.describe_left_out({"cells": 1, "nuclei": 3}, debug_pdf_written=True)
    assert text.endswith("They are outlined in red in the pairing PDF.")


@pytest.mark.parametrize("export_mode, shows_counts", [(BOTH, True), (NUCLEUS_ONLY, False), (WHOLE_CELL_ONLY, False)])
def test_paired_export_summary_adds_up_left_out_masks(export_mode, shows_counts, single_mode_spies):
    """Paired export totals the unpaired masks of every exported frame in the summary popup"""
    frames = [make_export_frame(sample, ["647"]) for sample in ("s001", "s002")]
    frames[0].get_pairings.return_value = {"unmatched_cytoplasms": [0, 4], "unmatched_nuclei": [1]}
    frames[1].get_pairings.return_value = {"unmatched_cytoplasms": [2], "unmatched_nuclei": []}
    for frame in frames:
        frame.has_nucleus_segments.return_value = True
    with patch.object(mat_export, "show_export_complete") as show:
        export_frames(frames, export_mode)
    summary = show.call_args.args[1]
    assert ("Left out (no partner): 3 whole-cell masks and 1 nucleus mask" in summary) == shows_counts


def test_paired_export_does_not_count_one_sided_masks_as_left_out(single_mode_spies):
    """Direct paired export writes no cells for one-sided frames and does not report unmatched masks."""
    writer, pairing, nucleus_only, whole_cell_only, debug_pdf = single_mode_spies
    nucleus_only_frame = make_export_frame("s001", ["647"], has_masks=False)
    nucleus_only_frame.has_nucleus_segments.return_value = True
    nucleus_only_frame.has_segments.return_value = False
    nucleus_only_frame.get_pairings.return_value = {"unmatched_cytoplasms": [], "unmatched_nuclei": [0, 1]}
    whole_cell_only_frame = make_export_frame("s002", ["647"], has_masks=True)
    whole_cell_only_frame.has_nucleus_segments.return_value = False
    whole_cell_only_frame.get_pairings.return_value = {"unmatched_cytoplasms": [0], "unmatched_nuclei": []}

    with patch.object(mat_export, "show_export_complete") as show:
        export_frames([nucleus_only_frame, whole_cell_only_frame], BOTH)

    pairing.assert_not_called()
    nucleus_only.assert_not_called()
    whole_cell_only.assert_not_called()
    writer.assert_called_once_with(["s001_w647.tif", "s002_w647.tif"], [[], []], [[], []], [[], []], "result.mat", dirname=".")
    summary = show.call_args.args[1]
    assert "Left out (no partner): 0 whole-cell masks and 0 nucleus masks" in summary
