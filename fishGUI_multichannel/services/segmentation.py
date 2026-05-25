# services/segmentation.py
import numpy as np
import logging
import time
from ..gui.canvas.segment import segment
from ..utils.image_preprocessing import compute_contrast

logger = logging.getLogger('fishcore')


def _masks_to_segments(masks: np.ndarray, gui) -> list[segment]:
    """
    Converts a mask array into a list of segment object defined in gui/canvas/segment.py
    """
    seg_objs = []
    for mask_id in np.unique(masks):
        if mask_id == 0:    # skip background
            continue
        mask = (masks == mask_id).astype(np.uint8)  # convert boolean array to a binary array (ensure compatibility with image processing libraries)
        seg_objs.append(segment(gui, mask))
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


def _segment_channel(fish_model, img, gui):
    """
    Run the model and convert masks to segment objects.
    """
    try:
        masks, flows = fish_model.predict(img)  # defined in fishCore.py
        return _masks_to_segments(masks, gui)   # convert each mask numpy array to segment object (defined in gui/canvas/segment.py)
    except Exception as e:
        logger.exception(f"Predict failed: {e}")
        return []


def run_cellpose_sam_segmentation(
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

    fish_model = gui.getBackEnd()
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
    seg_objs = _segment_channel(fish_model, img, gui)
    results[selected_channel] = seg_objs

    return results

