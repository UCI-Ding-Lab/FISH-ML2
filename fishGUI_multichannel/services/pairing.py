import pathlib
import logging
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from scipy.optimize import linear_sum_assignment

logger = logging.getLogger("fishcore")


def make_empty_pairing_result() -> dict:
    """Return an empty pairing result for one cytoplasm channel."""
    return {"pairs": [], "unmatched_nuclei": [], "unmatched_cytoplasms": []}


def clone_pairing_result(pairing_result: dict) -> dict:
    """Return a shallow copy of one pairing result with fresh list containers."""
    if pairing_result is None:
        return make_empty_pairing_result()
    return {
        "pairs": [dict(pair) for pair in pairing_result["pairs"]],
        "unmatched_nuclei": list(pairing_result["unmatched_nuclei"]),
        "unmatched_cytoplasms": list(pairing_result["unmatched_cytoplasms"]),
    }


def segment_to_mask(seg_obj) -> np.ndarray:
    """Convert one segment object into a boolean mask in image coordinates."""
    return seg_obj._segment__data.T.astype(bool)


def mask_center(mask: np.ndarray) -> tuple[float, float]:
    """Return the center of a mask as an `(x, y)` coordinate."""
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return 0.0, 0.0
    return float(xs.mean()), float(ys.mean())


def center_inside_mask(mask: np.ndarray, center: tuple[float, float]) -> bool:
    """Return True when the given `(x, y)` center lies inside the mask."""
    x, y = center
    xi = int(round(x))
    yi = int(round(y))
    if yi < 0 or xi < 0 or yi >= mask.shape[0] or xi >= mask.shape[1]:
        return False
    return bool(mask[yi, xi])


def nucleus_containment_score(nucleus_mask: np.ndarray, cytoplasm_mask: np.ndarray) -> float:
    """Return how much of the nucleus lies inside the cytoplasm mask."""
    nucleus_area = int(nucleus_mask.sum())
    if nucleus_area == 0:
        return 0.0
    overlap = np.logical_and(nucleus_mask, cytoplasm_mask).sum()
    return float(overlap) / float(nucleus_area)


def normalized_center_distance(
    nucleus_center: tuple[float, float],
    cytoplasm_center: tuple[float, float],
    image_shape: tuple[int, int],
) -> float:
    """Return the center distance normalized by the image diagonal."""
    height, width = image_shape
    diagonal = float(np.hypot(width, height))
    if diagonal == 0:
        return 1.0
    dx = nucleus_center[0] - cytoplasm_center[0]
    dy = nucleus_center[1] - cytoplasm_center[1]
    return min(float(np.hypot(dx, dy)) / diagonal, 1.0)


def build_pair_cost(nucleus_mask: np.ndarray, cytoplasm_mask: np.ndarray) -> tuple[float, bool, float, float]:
    """Build one pairing cost using containment first and distance as fallback."""
    nucleus_center = mask_center(nucleus_mask)
    cytoplasm_center = mask_center(cytoplasm_mask)
    center_inside = center_inside_mask(cytoplasm_mask, nucleus_center)
    containment = nucleus_containment_score(nucleus_mask, cytoplasm_mask)
    distance = normalized_center_distance(nucleus_center, cytoplasm_center, nucleus_mask.shape)
    penalty = 0.0 if center_inside else 2.0
    return penalty + (1.0 - containment) + distance, center_inside, containment, distance


def match_quality_is_good(center_inside: bool, containment: float, distance: float) -> bool:
    """Keep matches that contain the nucleus or are a strong spatial fallback."""
    if center_inside:
        return True
    if containment >= 0.2:
        return True
    return distance <= 0.1


def build_pairing_result(nucleus_segments: list, cytoplasm_segments: list) -> dict:
    """Pair DAPI nuclei to cytoplasm masks with Hungarian matching."""
    if not nucleus_segments or not cytoplasm_segments:
        result = make_empty_pairing_result()
        result["unmatched_nuclei"] = list(range(len(nucleus_segments)))
        result["unmatched_cytoplasms"] = list(range(len(cytoplasm_segments)))
        return result
    return _pair_non_empty_segments(nucleus_segments, cytoplasm_segments)


def _pair_non_empty_segments(nucleus_segments: list, cytoplasm_segments: list) -> dict:
    nucleus_masks = [segment_to_mask(seg) for seg in nucleus_segments]
    cytoplasm_masks = [segment_to_mask(seg) for seg in cytoplasm_segments]
    cost_matrix, meta = build_cost_matrix(nucleus_masks, cytoplasm_masks)
    rows, cols = linear_sum_assignment(cost_matrix)
    return finalize_pairing(rows, cols, meta, len(nucleus_masks), len(cytoplasm_masks))


def build_cost_matrix(nucleus_masks: list[np.ndarray], cytoplasm_masks: list[np.ndarray]) -> tuple[np.ndarray, dict]:
    """Build the Hungarian cost matrix and keep per-pair metadata."""
    cost_matrix = np.zeros((len(nucleus_masks), len(cytoplasm_masks)), dtype=np.float64)
    meta = {}
    for i, nucleus_mask in enumerate(nucleus_masks):
        for j, cytoplasm_mask in enumerate(cytoplasm_masks):
            cost, inside, containment, distance = build_pair_cost(nucleus_mask, cytoplasm_mask)
            cost_matrix[i, j] = cost
            meta[(i, j)] = (inside, containment, distance)
    return cost_matrix, meta


def finalize_pairing(rows, cols, meta: dict, nucleus_count: int, cytoplasm_count: int) -> dict:
    """Turn Hungarian assignments into clean pairs plus unmatched indices."""
    pairs = collect_valid_pairs(rows, cols, meta)
    pairs = remove_ambiguous_pairs(pairs, meta)
    return build_result_from_pairs(pairs, nucleus_count, cytoplasm_count)


def collect_valid_pairs(rows, cols, meta: dict) -> list[dict]:
    """Collect the Hungarian matches that pass the basic pairing quality rule."""
    pairs = []
    for pair_index, (row, col) in enumerate(zip(rows, cols), start=1):
        pair = build_valid_pair(pair_index, row, col, meta)
        if pair is not None:
            pairs.append(pair)
    return pairs


def build_valid_pair(pair_index: int, row: int, col: int, meta: dict) -> dict | None:
    """Build one pair when the nucleus and cytoplasm look like a valid match."""
    center_inside, containment, distance = meta[(row, col)]
    if not match_quality_is_good(center_inside, containment, distance):
        return None
    return build_pair_entry(pair_index, row, col, center_inside, containment, distance)


def remove_ambiguous_pairs(pairs: list[dict], meta: dict) -> list[dict]:
    """Keep only pairs whose cytoplasm contains one nucleus center."""
    clean_pairs = []
    for pair in pairs:
        if pair_is_ambiguous(pair, meta):
            continue
        clean_pairs.append(pair)
    return clean_pairs


def pair_is_ambiguous(pair: dict, meta: dict) -> bool:
    """Return True when a pair's cytoplasm has more than one nucleus center inside."""
    cytoplasm_index = pair["cytoplasm_index"]
    return count_nuclei_inside_cytoplasm(cytoplasm_index, meta) > 1


def count_nuclei_inside_cytoplasm(cytoplasm_index: int, meta: dict) -> int:
    """Count how many nucleus centers fall inside one cytoplasm mask."""
    inside_count = 0
    for nucleus_cytoplasm, values in meta.items():
        if not is_same_cytoplasm(nucleus_cytoplasm, cytoplasm_index):
            continue
        if nucleus_center_is_inside(values):
            inside_count += 1
    return inside_count


def is_same_cytoplasm(nucleus_cytoplasm: tuple[int, int], cytoplasm_index: int) -> bool:
    """Return True when one metadata entry belongs to the requested cytoplasm."""
    return nucleus_cytoplasm[1] == cytoplasm_index


def nucleus_center_is_inside(values: tuple[bool, float, float]) -> bool:
    """Return True when one nucleus center lies inside the cytoplasm mask."""
    center_inside, _, _ = values
    return center_inside


def build_result_from_pairs(pairs: list[dict], nucleus_count: int, cytoplasm_count: int) -> dict:
    """Build the final pairing result using the accepted clean pairs."""
    result = make_empty_pairing_result()
    result["pairs"] = pairs
    matched_nuclei = {pair["nucleus_index"] for pair in pairs}
    matched_cytoplasms = {pair["cytoplasm_index"] for pair in pairs}
    result["unmatched_nuclei"] = collect_unmatched_indices(nucleus_count, matched_nuclei)
    result["unmatched_cytoplasms"] = collect_unmatched_indices(cytoplasm_count, matched_cytoplasms)
    return result


def build_pair_entry(pair_index: int, nucleus_index: int, cytoplasm_index: int, center_inside: bool, containment: float, distance: float) -> dict:
    """Build one readable record describing a matched nucleus/cytoplasm pair."""
    return {
        "pair_index": pair_index,
        "nucleus_index": int(nucleus_index),
        "cytoplasm_index": int(cytoplasm_index),
        "center_inside": bool(center_inside),
        "containment": float(containment),
        "distance": float(distance),
    }


def collect_unmatched_indices(total_count: int, matched_indices: set[int]) -> list[int]:
    """Return every index from `0..N-1` that was not accepted as a match."""
    return [index for index in range(total_count) if index not in matched_indices]


def export_pairing_debug_pdf(frames: list, output_dir: pathlib.Path) -> pathlib.Path | None:
    """Save one PDF that shows numbered cytoplasm and nucleus pairs per frame."""
    pages = collect_pairing_debug_pages(frames)
    if not pages:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"{output_dir.name}_pairing_debug.pdf"
    return write_pairing_debug_pdf_pages(pdf_path, pages)


def write_pairing_debug_pdf_pages(pdf_path: pathlib.Path, pages: list[tuple]) -> pathlib.Path | None:
    """Write pairing debug pages and skip the PDF cleanly if drawing fails."""
    try:
        with PdfPages(pdf_path) as pdf:
            for frame, channel, pairing in pages:
                save_pairing_debug_page(pdf, frame, channel, pairing)
    except Exception as error:
        remove_partial_pairing_pdf(pdf_path)
        logger.warning("Skipped pairing debug PDF export: %s", error)
        return None
    return pdf_path


def save_pairing_debug_page(pdf, frame, channel: str, pairing: dict) -> None:
    """Render one frame-and-channel pairing page into the PDF."""
    figure = create_pairing_figure(frame, channel, pairing)
    pdf.savefig(figure, bbox_inches="tight")
    figure.clear()


def remove_partial_pairing_pdf(pdf_path: pathlib.Path) -> None:
    """Delete an unfinished PDF so export does not leave broken files behind."""
    if pdf_path.exists():
        pdf_path.unlink()
        


def collect_pairing_debug_pages(frames: list) -> list[tuple]:
    """Return the frame/channel combinations that currently have pairing data."""
    pages = []
    for frame in frames:
        for channel in frame.available_channels:
            pairing = frame.get_pairings(channel)
            if pairing["pairs"] or pairing["unmatched_nuclei"] or pairing["unmatched_cytoplasms"]:
                pages.append((frame, channel, pairing))
    return pages


def create_pairing_figure(frame, channel: str, pairing: dict):
    """Build one PDF page with cytoplasm on the left and DAPI on the right."""
    figure = Figure(figsize=(12, 6))
    axes = figure.subplots(1, 2)
    figure.suptitle(f"Sample {frame.sample_id} channel {channel} pairing")
    draw_channel_panel(axes[0], frame.getImgNumpyRGBForChannel(channel), frame.get_segments(channel), pairing, "cytoplasm")
    draw_channel_panel(axes[1], frame.getImgNumpyRGBForChannel("DAPI"), frame.get_nucleus_segments(), pairing, "nucleus")
    return figure


def draw_channel_panel(axis, image: np.ndarray, seg_objs: list, pairing: dict, target: str) -> None:
    """Draw one channel image and label its matched and unmatched masks."""
    axis.imshow(image)
    axis.set_title(target.capitalize())
    axis.axis("off")
    draw_matched_masks(axis, seg_objs, pairing["pairs"], target)
    draw_unmatched_masks(axis, seg_objs, pairing, target)


def draw_matched_masks(axis, seg_objs: list, pairs: list[dict], target: str) -> None:
    """Draw matched masks and place the shared pair number at each mask center."""
    index_key = "nucleus_index" if target == "nucleus" else "cytoplasm_index"
    for pair in pairs:
        seg_obj = seg_objs[pair[index_key]]
        draw_mask_outline(axis, seg_obj, "lime")
        x, y = get_segment_label_position(seg_obj)
        axis.text(x, y, str(pair["pair_index"]), color="yellow", fontsize=10, weight="bold")


def draw_unmatched_masks(axis, seg_objs: list, pairing: dict, target: str) -> None:
    """Draw unmatched masks with readable prefixes so odd cases are easy to inspect."""
    unmatched_key = "unmatched_nuclei" if target == "nucleus" else "unmatched_cytoplasms"
    prefix = "N" if target == "nucleus" else "C"
    for offset, mask_index in enumerate(pairing[unmatched_key], start=1):
        seg_obj = seg_objs[mask_index]
        draw_mask_outline(axis, seg_obj, "red")
        x, y = get_segment_label_position(seg_obj)
        axis.text(x, y, f"{prefix}{offset}", color="red", fontsize=9, weight="bold")


def get_segment_label_position(seg_obj) -> tuple[float, float]:
    """Return a readable label position near the middle of one segment."""
    return mask_center(segment_to_mask(seg_obj))


def draw_mask_outline(axis, seg_obj, color: str) -> None:
    """Draw one segment outline by reusing the segment's stored path."""
    axis.add_patch(build_outline_patch(seg_obj, color))


def build_outline_patch(seg_obj, color: str) -> PathPatch:
    """Build a fresh outline patch so one segment can be drawn on many figures."""
    path = seg_obj.patch.get_path()
    vertices = np.array(path.vertices, copy=True)
    codes = None if path.codes is None else np.array(path.codes, copy=True)
    return PathPatch(Path(vertices, codes), facecolor="none", edgecolor=color, linewidth=1.0)
