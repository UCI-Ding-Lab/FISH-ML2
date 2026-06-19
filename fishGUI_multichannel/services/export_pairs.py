import pathlib
import re


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
    pairs = abs_obj.get_pairings(channel)["pairs"]
    xy = collect_pair_xy(abs_obj, channel, pairs)
    masks = collect_pair_masks(abs_obj, channel, pairs)
    nucleus_masks = collect_pair_nucleus_masks(abs_obj, pairs)
    return xy, masks, nucleus_masks


def collect_pair_xy(abs_obj, channel: str, pairs: list[dict]) -> list:
    """
    Collect the cytoplasm center positions for every matched cell pair.
    """
    segs = abs_obj.get_segments(channel)
    return [segs[pair["cytoplasm_index"]].xy for pair in pairs]


def collect_pair_masks(abs_obj, channel: str, pairs: list[dict]) -> list:
    """
    Collect the cytoplasm masks for every matched cell pair.
    """
    segs = abs_obj.get_segments(channel)
    return [segs[pair["cytoplasm_index"]].box for pair in pairs]


def collect_pair_nucleus_masks(abs_obj, pairs: list[dict]) -> list:
    """
    Collect the paired nucleus masks for every matched cell pair.
    """
    nuclei = abs_obj.get_nucleus_segments()
    return [nuclei[pair["nucleus_index"]].box for pair in pairs]
