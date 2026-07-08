# services/segmentation.py
import numpy as np
import logging
import time
from ..gui.canvas.segment import segment
from ..utils.image_preprocessing import compute_contrast

logger = logging.getLogger('fishcore')


def _label_mask_to_segments(masks: np.ndarray, gui) -> list[segment]:
    """
    Convert one labeled 2D mask image into segment objects.
    """
    seg_objs = []
    for mask_id in np.unique(masks):
        if mask_id == 0:    # skip background
            continue
        mask = (masks == mask_id).astype(np.uint8)  # convert boolean array to a binary array (ensure compatibility with image processing libraries)
        seg_objs.append(segment(gui, mask))
    return seg_objs


def _mask_stack_to_segments(mask_stack: np.ndarray, gui) -> list[segment]:
    """
    Convert one stack of 2D binary masks into segment objects.
    """
    seg_objs = []
    for mask in mask_stack:
        squeezed_mask = np.squeeze(mask).astype(np.uint8)
        if squeezed_mask.ndim != 2:
            continue
        if not np.any(squeezed_mask):
            continue
        seg_objs.append(segment(gui, squeezed_mask))
    return seg_objs


def _select_best_cyto2(main_channel: str, cyto_channels: dict) -> np.ndarray:
    candidates = [(k, v) for k, v in cyto_channels.items() if k != main_channel and v is not None]
    if not candidates:
        return None
    best = max(candidates, key=lambda kv: compute_contrast(kv[1]))
    return best[1]


def _prepare_segmentation_input(nucleus_img, cyto1, cyto2):
    """
    Stack nucleus, cyto1, cyto2 into a 3-channel float32 image for model input.
    """
    return np.stack([nucleus_img, cyto1, cyto2], axis=-1).astype(np.float32, copy=False)


def _segment_mask_array(mask_output, gui) -> list[segment]:
    """
    Convert one backend mask output into segment objects.
    """
    if isinstance(mask_output, tuple):
        masks = mask_output[0]
    else:
        masks = mask_output
    masks = np.asarray(masks)
    if masks.ndim == 2:
        return _label_mask_to_segments(masks, gui)
    if masks.ndim == 3:
        return _mask_stack_to_segments(masks, gui)
    return []


def run_nucleus_segmentation(nucleus_img: np.ndarray, gui, sample_id, bbox_list=None) -> list[segment]:
    """
    Segment nuclei with the selected nucleus backend and return segment objects.
    """
    logger.info("Starting nucleus segmentation for sample %s ...", sample_id)
    if nucleus_img is None:
        logger.warning("Nucleus segmentation aborted for sample %s: missing DAPI image", sample_id)
        return []

    nucleus_backend = gui.getNucleusBackend()
    try:
        mask_output = nucleus_backend.predict_nucleus(nucleus_img, bbox_list)
        return _segment_mask_array(mask_output, gui)
    except Exception as error:
        logger.exception("Nucleus predict failed: %s", error)
        return []


def run_cytoplasm_segmentation(
    nucleus_img: np.ndarray,
    cyto_channels: dict,
    gui,
    selected_channel: str,
):
    """
    Segment only the selected channel.
    Return a dict with all channels present, but only the selected one populated.
    """
    logger.info(f"Starting segmentation (Cellpose-SAM predict) for channel {selected_channel} ...")

    cytoplasm_backend = gui.getCytoplasmBackend()
    results = {k: [] for k in cyto_channels}
    if not cyto_channels or nucleus_img is None:
        logger.warning("Segmentation aborted: missing nucleus or cytoplasm channel")
        return results

    cyto1 = cyto_channels.get(selected_channel)
    if cyto1 is None:
        logger.warning(f"Segmentation aborted: missing selected channel {selected_channel}")
        return results
    cyto2 = _select_best_cyto2(selected_channel, cyto_channels)
    if cyto2 is None:
        cyto2 = np.zeros_like(cyto1)

    img = _prepare_segmentation_input(nucleus_img, cyto1, cyto2)
    try:
        mask_output = cytoplasm_backend.predict_cytoplasm(img)
        results[selected_channel] = _segment_mask_array(mask_output, gui)
    except Exception as e:
        logger.exception(f"Cytoplasm predict failed: {e}")

    return results

