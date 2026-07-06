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
        ("img_s001_w488_s001.tif", "001", "488"),
        ("MAX_EXP_w488_s0026.tif", "0026", "488"),
        ("img_s012_w514_s012.tif", "012", "514"),
        ("img_S003_w555_S003.tif", "003", "555"),
    ],
)
def test_parse_sample_id_and_channel_accepts_valid_filenames(
    workspace_temp_dir, filename, expected_sample, expected_channel
):
    path = workspace_temp_dir / filename
    path.touch()

    sample_id, channel = parse_sample_id_and_channel(path)

    assert sample_id == expected_sample
    assert channel == expected_channel


@pytest.mark.parametrize(
    "filename",
    [
        "nucleus.tif",
        "img_s001_w647.tif",
        "random_file.txt",
        "MAX_EXP_w488_nosample.tif",
    ],
)
def test_parse_sample_id_and_channel_returns_none_for_invalid_filenames(
    workspace_temp_dir, filename
):
    path = workspace_temp_dir / filename
    path.touch()

    assert parse_sample_id_and_channel(path) == (None, None)


def test_group_files_by_sample_and_channel_groups_paths_by_sample_and_channel(
    workspace_temp_dir,
):
    sample1_dapi = workspace_temp_dir / "img_s001_wDAPI_s001.tif"
    sample1_647 = workspace_temp_dir / "img_s001_w647_s001.tif"
    sample1_488 = workspace_temp_dir / "img_s001_w488_s001.tif"
    sample2_dapi = workspace_temp_dir / "img_s002_wDAPI_s002.tif"
    sample2_555 = workspace_temp_dir / "img_s002_w555_s002.tif"
    for path in (sample1_dapi, sample1_647, sample1_488, sample2_dapi, sample2_555):
        path.touch()

    grouped = group_files_by_sample_and_channel(
        [sample1_647, sample2_555, sample1_dapi, sample2_dapi, sample1_488]
    )

    assert grouped == {
        "001": {
            "647": sample1_647,
            "DAPI": sample1_dapi,
            "488": sample1_488,
        },
        "002": {
            "555": sample2_555,
            "DAPI": sample2_dapi,
        },
    }


def test_group_files_by_sample_and_channel_invokes_parse_error_callback(workspace_temp_dir):
    valid = workspace_temp_dir / "img_s001_w647_s001.tif"
    invalid = workspace_temp_dir / "bad_file.tif"
    valid.touch()
    invalid.touch()
    on_error = MagicMock()

    grouped = group_files_by_sample_and_channel(
        [valid, invalid],
        on_parse_error=on_error,
    )

    assert grouped == {"001": {"647": valid}}
    on_error.assert_called_once_with(invalid)


def test_get_cytoplasm_paths_and_names_excludes_dapi(workspace_temp_dir):
    dapi = workspace_temp_dir / "img_s001_wDAPI_s001.tif"
    cyto_647 = workspace_temp_dir / "img_s001_w647_s001.tif"
    cyto_488 = workspace_temp_dir / "img_s001_w488_s001.tif"
    channels = {"DAPI": dapi, "647": cyto_647, "488": cyto_488}

    cyto_paths, cyto_channels = get_cytoplasm_paths_and_names(channels)

    assert cyto_paths == [cyto_647, cyto_488]
    assert cyto_channels == ["647", "488"]


def test_channels_from_paths_rebuilds_channel_dict_for_session_load(workspace_temp_dir):
    nucleus = workspace_temp_dir / "img_s001_wDAPI_s001.tif"
    cyto_647 = workspace_temp_dir / "img_s001_w647_s001.tif"
    cyto_488 = workspace_temp_dir / "img_s001_w488_s001.tif"
    for path in (nucleus, cyto_647, cyto_488):
        path.touch()

    channels = channels_from_paths(nucleus, [cyto_647, cyto_488])

    assert channels == {
        "DAPI": nucleus,
        "647": cyto_647,
        "488": cyto_488,
    }


def test_channels_from_paths_falls_back_to_dapi_when_nucleus_is_unparsed(workspace_temp_dir):
    nucleus = workspace_temp_dir / "unparsed_nucleus.tif"
    cyto_647 = workspace_temp_dir / "img_s001_w647_s001.tif"
    nucleus.touch()
    cyto_647.touch()

    channels = channels_from_paths(nucleus, [cyto_647])

    assert channels == {"DAPI": nucleus, "647": cyto_647}


def test_undocumented_channels_in_grouped_returns_sorted_unknown_channels():
    grouped = {
        "001": {
            "DAPI": pathlib.Path("img_s001_wDAPI_s001.tif"),
            "647": pathlib.Path("img_s001_w647_s001.tif"),
            "CUSTOM": pathlib.Path("img_s001_wCUSTOM_s001.tif"),
        },
        "002": {
            "DAPI": pathlib.Path("img_s002_wDAPI_s002.tif"),
            "NEWCH": pathlib.Path("img_s002_wNEWCH_s002.tif"),
            "647": pathlib.Path("img_s002_w647_s002.tif"),
        },
    }

    assert undocumented_channels_in_grouped(grouped) == ["CUSTOM", "NEWCH"]


def test_documented_and_allowed_channel_sets_include_expected_values():
    assert DOCUMENTED_CHANNELS == frozenset({"647", "488", "514", "555", "594"})
    assert ALLOWED_CHANNELS == DOCUMENTED_CHANNELS | {"DAPI"}
