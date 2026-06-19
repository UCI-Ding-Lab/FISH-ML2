import pathlib
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from scipy.optimize import linear_sum_assignment


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
    """Turn Hungarian assignments into accepted pairs plus unmatched indices."""
    result = make_empty_pairing_result()
    matched_nuclei = set()
    matched_cytoplasms = set()
    for pair_index, (row, col) in enumerate(zip(rows, cols), start=1):
        center_inside, containment, distance = meta[(row, col)]
        if not match_quality_is_good(center_inside, containment, distance):
            continue
        result["pairs"].append(build_pair_entry(pair_index, row, col, center_inside, containment, distance))
        matched_nuclei.add(int(row))
        matched_cytoplasms.add(int(col))
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
    with PdfPages(pdf_path) as pdf:
        for frame, channel, pairing in pages:
            fig = create_pairing_figure(frame, channel, pairing)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
    return pdf_path


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
    figure, axes = plt.subplots(1, 2, figsize=(12, 6))
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
        mask = segment_to_mask(seg_objs[pair[index_key]])
        draw_mask_outline(axis, mask, "lime")
        x, y = mask_center(mask)
        axis.text(x, y, str(pair["pair_index"]), color="yellow", fontsize=10, weight="bold")


def draw_unmatched_masks(axis, seg_objs: list, pairing: dict, target: str) -> None:
    """Draw unmatched masks with readable prefixes so odd cases are easy to inspect."""
    unmatched_key = "unmatched_nuclei" if target == "nucleus" else "unmatched_cytoplasms"
    prefix = "N" if target == "nucleus" else "C"
    for offset, mask_index in enumerate(pairing[unmatched_key], start=1):
        mask = segment_to_mask(seg_objs[mask_index])
        draw_mask_outline(axis, mask, "red")
        x, y = mask_center(mask)
        axis.text(x, y, f"{prefix}{offset}", color="red", fontsize=9, weight="bold")


def draw_mask_outline(axis, mask: np.ndarray, color: str) -> None:
    """Draw one binary mask as a contour on the given matplotlib axis."""
    axis.contour(mask.astype(float), levels=[0.5], colors=[color], linewidths=1.0)
