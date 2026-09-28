from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from fishGUI_multichannel.services import progress
from fishGUI_multichannel.services.session_manager import SessionManager


def make_export_frame(sample_id, channels, selected=True, has_masks=True):
    """Build a sample with ordered image channels without loading real images"""
    frame = MagicMock(selected=selected)
    frame.getCytoplasmChannelsAndPaths.return_value = {
        channel: Path(f"{sample_id}_w{channel}.tif") for channel in channels
    }
    frame.has_segments.return_value = has_masks
    return frame


@pytest.fixture
def export_spies():
    """Capture exported data while replacing dialogs and file writing"""
    with (
        patch.object(progress.filedialog, "asksaveasfilename", return_value="result.mat"),
        patch.object(progress, "create") as writer,
        patch.object(progress, "build_paired_export_data", return_value=([(1, 1)], ["cell"], ["nucleus"])) as pairing,
    ):
        yield writer, pairing


def export_frames(frames):
    """Run the export action on sample doubles with optional PDF output disabled"""
    gui = MagicMock()
    gui.shouldExportPairingDebugPdf.return_value = False
    with patch.object(SessionManager, "getPool", return_value=frames):
        progress.Progress.export(gui)


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
