import pathlib
import re

from .pairing import segment_to_mask


def extract_export_channel(path: pathlib.Path) -> str | None:
    """
    Read the cytoplasm channel number from one image filename.
    """
    match = re.search(r"(647|488|555|594|514)", path.stem.lower())
    return match.group(1) if match else None


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
