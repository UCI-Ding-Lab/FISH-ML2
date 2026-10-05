import pathlib

from ..utils.sample_channels import parse_sample_id_and_channel
from .pairing import segment_to_mask


def extract_export_channel(path: pathlib.Path) -> str | None:
    """
    Read the cytoplasm channel name from one image filename.
    """
    _, channel = parse_sample_id_and_channel(path)
    return channel


def first_cytoplasm_channel_and_path(frame) -> tuple[str, pathlib.Path] | None:
    """
    Return the cytoplasm channel and image path that export uses for one frame, or None.
    """
    channel_items = list(frame.getCytoplasmChannelsAndPaths().items())
    return channel_items[0] if channel_items else None


def frame_is_dapi_only(frame) -> bool:
    """
    Return True when one frame has a DAPI image but no cytoplasm channel images.
    """
    return first_cytoplasm_channel_and_path(frame) is None


def all_selected_frames_are_dapi_only(frames: list) -> bool:
    """
    Return True when there is at least one selected frame and every selected frame is DAPI-only.
    """
    selected = [frame for frame in frames if frame.selected]
    return bool(selected) and all(frame_is_dapi_only(frame) for frame in selected)


def frame_has_whole_cell_masks(frame) -> bool:
    """
    Return True when the exported cytoplasm channel of one frame has whole-cell masks.
    """
    first_channel = first_cytoplasm_channel_and_path(frame)
    return first_channel is not None and frame.has_segments(first_channel[0])


def build_paired_export_data(abs_obj, channel: str) -> tuple[list, list, list]:
    """
    Build matched cell positions plus cytoplasm and nucleus masks for one channel.
    """
    abs_obj.update_pairings_for_channel(channel)
    pairs = collect_valid_export_pairs(abs_obj, channel)
    cells = collect_export_cells(abs_obj, channel, pairs)
    xy = [cell["pos"] for cell in cells]
    masks = [cell["mask"] for cell in cells]
    nucleus_masks = [cell["nucleus_mask"] for cell in cells]
    return xy, masks, nucleus_masks


def build_nucleus_only_export_data(abs_obj) -> tuple[list, list]:
    """
    Build cell positions and masks from every nucleus mask, without pairing.
    """
    return build_single_mask_export_data(abs_obj.get_nucleus_segments())


def build_whole_cell_only_export_data(abs_obj, channel: str) -> tuple[list, list]:
    """
    Build cell positions and masks from every whole-cell mask of one channel, without pairing.
    """
    return build_single_mask_export_data(abs_obj.get_segments(channel))


def build_single_mask_export_data(segs: list) -> tuple[list, list]:
    """
    Crop each segment to its own bounds and return matching positions and masks.
    """
    cells = [build_single_mask_cell(segment_to_mask(seg)) for seg in segs]
    xy = [cell["pos"] for cell in cells]
    masks = [cell["mask"] for cell in cells]
    return xy, masks


def build_single_mask_cell(mask: object) -> dict:
    """
    Build one export cell from a single full-image mask.
    """
    bounds = collect_mask_bounds(mask)
    return {
        "pos": build_export_position(bounds),
        "mask": crop_mask(mask, bounds),
    }


def collect_valid_export_pairs(abs_obj, channel: str) -> list[dict]:
    """
    Return only pairs whose nucleus and cytoplasm indexes still exist for export.
    """
    pairs = abs_obj.get_pairings(channel)["pairs"]
    segs = abs_obj.get_segments(channel)
    nuclei = abs_obj.get_nucleus_segments()
    return [pair for pair in pairs if pair_indexes_exist(pair, segs, nuclei)]


def pair_indexes_exist(pair: dict, segs: list, nuclei: list) -> bool:
    """
    Return True when one pair points to existing cytoplasm and nucleus masks.
    """
    cyto_index = pair["cytoplasm_index"]
    nucleus_index = pair["nucleus_index"]
    return cyto_index < len(segs) and nucleus_index < len(nuclei)


def collect_export_cells(abs_obj, channel: str, pairs: list[dict]) -> list[dict]:
    """
    Build aligned export data so both masks share one crop and one position.
    """
    segs = abs_obj.get_segments(channel)
    nuclei = abs_obj.get_nucleus_segments()
    return [build_export_cell(pair, segs, nuclei) for pair in pairs]


def build_export_cell(pair: dict, segs: list, nuclei: list) -> dict:
    """
    Build one export cell using a shared crop for cytoplasm and nucleus masks.
    """
    cyto_mask = segment_to_mask(segs[pair["cytoplasm_index"]])
    nucleus_mask = segment_to_mask(nuclei[pair["nucleus_index"]])
    bounds = collect_shared_bounds(cyto_mask, nucleus_mask)
    return {
        "pos": build_export_position(bounds),
        "mask": crop_mask(cyto_mask, bounds),
        "nucleus_mask": crop_mask(nucleus_mask, bounds),
    }


def collect_shared_bounds(cyto_mask: object, nucleus_mask: object) -> tuple[int, int, int, int]:
    """
    Return one bounding box that covers both masks in image coordinates.
    """
    cyto_bounds = collect_mask_bounds(cyto_mask)
    nucleus_bounds = collect_mask_bounds(nucleus_mask)
    top = min(cyto_bounds[0], nucleus_bounds[0])
    left = min(cyto_bounds[1], nucleus_bounds[1])
    bottom = max(cyto_bounds[2], nucleus_bounds[2])
    right = max(cyto_bounds[3], nucleus_bounds[3])
    return top, left, bottom, right


def collect_mask_bounds(mask: object) -> tuple[int, int, int, int]:
    """
    Return the top, left, bottom, and right edges of one full-image mask.
    """
    rows, cols = mask.nonzero()
    return rows.min(), cols.min(), rows.max(), cols.max()


def build_export_position(bounds: tuple[int, int, int, int]) -> tuple[int, int]:
    """
    Return the one-based top-left position expected by the MATLAB workflow.
    """
    top, left, _, _ = bounds
    return top + 1, left + 1


def crop_mask(mask: object, bounds: tuple[int, int, int, int]) -> object:
    """
    Crop one full-image mask to the shared export bounds for one cell.
    """
    top, left, bottom, right = bounds
    return mask[top : bottom + 1, left : right + 1]
