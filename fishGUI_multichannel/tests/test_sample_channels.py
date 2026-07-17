import pathlib
from unittest.mock import MagicMock

import pytest

from fishGUI_multichannel.utils.sample_channels import (
    ALLOWED_CHANNELS,
    DOCUMENTED_CHANNELS,
    channels_from_paths,
    get_cytoplasm_paths_and_names,
    group_files_by_sample_and_channel,
    parse_sample_id_and_channel,
    undocumented_channels_in_grouped,
)


@pytest.mark.parametrize(
    "filename, expected_sample, expected_channel",
    [
        ("img_s001_wDAPI_s001.tif", "001", "DAPI"),
        ("img_s001_w647_s001.tif", "001", "647"),
        ("img_s001_w647.tif", "001", "647"),
        ("MAX_EXP_w488_s0026.tif", "0026", "488"),
        ("img_s012_w514_s012.tif", "012", "514"),
        ("img_S003_wCUSTOM_S003.tif", "003", "CUSTOM"),
    ],
)
def test_parse_sample_id_and_channel_accepts_valid_filenames(
    workspace_temp_dir, filename, expected_sample, expected_channel
):
    """Parse supported sample and channel filename patterns."""
    path = workspace_temp_dir / filename
    path.touch()
    assert parse_sample_id_and_channel(path) == (expected_sample, expected_channel)


@pytest.mark.parametrize(
    "filename",
    ["nucleus.tif", "random_file.txt", "MAX_EXP_w488_nosample.tif"],
)
def test_parse_sample_id_and_channel_returns_none_for_invalid_filenames(
    workspace_temp_dir, filename
):
    """Return empty parse values when a filename lacks sample or channel data."""
    path = workspace_temp_dir / filename
    path.touch()
    assert parse_sample_id_and_channel(path) == (None, None)


def test_group_files_by_sample_and_channel_groups_paths(workspace_temp_dir):
    """Group imported paths by sample and parsed channel name."""
    sample1_dapi = workspace_temp_dir / "img_s001_wDAPI_s001.tif"
    sample1_647 = workspace_temp_dir / "img_s001_w647_s001.tif"
    sample2_custom = workspace_temp_dir / "img_s002_wCUSTOM_s002.tif"
    sample2_dapi = workspace_temp_dir / "img_s002_wDAPI_s002.tif"
    grouped = group_files_by_sample_and_channel([sample1_647, sample2_custom, sample1_dapi, sample2_dapi])
    assert grouped["001"] == {"647": sample1_647, "DAPI": sample1_dapi}
    assert grouped["002"] == {"CUSTOM": sample2_custom, "DAPI": sample2_dapi}


def test_group_files_by_sample_and_channel_invokes_parse_error_callback(workspace_temp_dir):
    """Call the parse-error callback for files that cannot be grouped."""
    valid = workspace_temp_dir / "img_s001_w647_s001.tif"
    invalid = workspace_temp_dir / "bad_file.tif"
    on_error = MagicMock()
    grouped = group_files_by_sample_and_channel([valid, invalid], on_parse_error=on_error)
    assert grouped == {"001": {"647": valid}}
    on_error.assert_called_once_with(invalid)


def test_get_cytoplasm_paths_and_names_excludes_dapi(workspace_temp_dir):
    """Return only non-DAPI paths and channel names."""
    dapi = workspace_temp_dir / "img_s001_wDAPI_s001.tif"
    cyto_647 = workspace_temp_dir / "img_s001_w647_s001.tif"
    channels = {"DAPI": dapi, "647": cyto_647}
    assert get_cytoplasm_paths_and_names(channels) == ([cyto_647], ["647"])


def test_channels_from_paths_rebuilds_channel_dict_for_session_load(workspace_temp_dir):
    """Rebuild the channel mapping saved sessions need during loading."""
    nucleus = workspace_temp_dir / "img_s001_wDAPI_s001.tif"
    cyto_647 = workspace_temp_dir / "img_s001_w647_s001.tif"
    channels = channels_from_paths(nucleus, [cyto_647])
    assert channels == {"DAPI": nucleus, "647": cyto_647}


def test_channels_from_paths_falls_back_to_dapi_when_nucleus_is_unparsed(workspace_temp_dir):
    """Use DAPI when a saved nucleus path does not parse cleanly."""
    nucleus = workspace_temp_dir / "unparsed_nucleus.tif"
    cyto_647 = workspace_temp_dir / "img_s001_w647_s001.tif"
    channels = channels_from_paths(nucleus, [cyto_647])
    assert channels == {"DAPI": nucleus, "647": cyto_647}


def test_undocumented_channels_in_grouped_returns_sorted_unknown_channels():
    """Return only imported channels that do not have tuned defaults."""
    grouped = {
        "001": {"DAPI": pathlib.Path("dapi.tif"), "CUSTOM": pathlib.Path("custom.tif")},
        "002": {"NEWCH": pathlib.Path("newch.tif"), "647": pathlib.Path("647.tif")},
    }
    assert undocumented_channels_in_grouped(grouped) == ["CUSTOM", "NEWCH"]


def test_documented_and_allowed_channel_sets_include_expected_values():
    """Keep documented and allowed channel constants explicit."""
    assert DOCUMENTED_CHANNELS == frozenset({"647", "488", "514", "555", "594"})
    assert ALLOWED_CHANNELS == DOCUMENTED_CHANNELS | {"DAPI"}
