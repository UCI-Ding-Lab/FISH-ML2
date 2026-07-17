"""
Parse sample IDs and imaging channels from TIFF filenames.

These helpers are shared by import and progress loading so channel names stay
consistent across the GUI.
"""
from __future__ import annotations

import logging
import pathlib
import re
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

DOCUMENTED_CHANNELS = frozenset({"647", "488", "514", "555", "594"})
ALLOWED_CHANNELS = DOCUMENTED_CHANNELS | {"DAPI"}


def parse_sample_id_and_channel(path: pathlib.Path) -> tuple[str | None, str | None]:
    """Return the sample id and channel name parsed from one TIFF path."""
    stem = path.stem
    sample_match = re.search(r"s(\d{1,4})", stem, re.IGNORECASE)
    channel_match = re.search(r"(?:^|[_-])w[-_]?(DAPI|\d{3}|[A-Za-z]+)(?=$|[_-])", stem, re.IGNORECASE)
    if not sample_match or not channel_match:
        logger.warning("Could not parse sample/channel from %r", stem)
        return None, None
    return sample_match.group(1), channel_match.group(1).upper()


def group_files_by_sample_and_channel(
    file_paths: list[pathlib.Path | str],
    *,
    on_parse_error: Callable[[pathlib.Path], Any] | None = None,
) -> dict[str, dict[str, pathlib.Path]]:
    """Group paths into {sample_id: {channel_name: path}}."""
    grouped: dict[str, dict[str, pathlib.Path]] = {}
    for file_path in file_paths:
        path = pathlib.Path(file_path)
        sample_id, channel_name = parse_sample_id_and_channel(path)
        if sample_id and channel_name:
            grouped.setdefault(sample_id, {})[channel_name] = path
        elif on_parse_error is not None:
            on_parse_error(path)
    return grouped


def get_cytoplasm_paths_and_names(
    channels: dict[str, pathlib.Path],
) -> tuple[list[pathlib.Path], list[str]]:
    """Return cytoplasm paths and channel names while excluding DAPI."""
    cyto_paths: list[pathlib.Path] = []
    cyto_channels: list[str] = []
    for channel, path in channels.items():
        if channel == "DAPI":
            continue
        cyto_paths.append(path)
        cyto_channels.append(channel)
    return cyto_paths, cyto_channels


def channels_from_paths(
    nucleus_path: pathlib.Path,
    cyto_paths: list[pathlib.Path],
) -> dict[str, pathlib.Path]:
    """Build {channel: path} for one sample during session loading."""
    channels: dict[str, pathlib.Path] = {}
    _, nucleus_channel = parse_sample_id_and_channel(nucleus_path)
    channels[nucleus_channel or "DAPI"] = nucleus_path
    for path in cyto_paths:
        _, cyto_channel = parse_sample_id_and_channel(path)
        if cyto_channel:
            channels[cyto_channel] = path
    return channels


def undocumented_channels_in_grouped(
    grouped: dict[str, dict[str, pathlib.Path]],
) -> list[str]:
    """Return sorted channel names that are imported with warning-only support."""
    found = {
        channel
        for channels in grouped.values()
        for channel in channels
        if channel not in ALLOWED_CHANNELS
    }
    return sorted(found)
