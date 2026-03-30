# services/segmentation.py
import numpy as np
import logging
import time
from ..gui.canvas.segment import segment

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


def run_cellpose_sam_segmentation(
    nucleus_img: np.ndarray,
    cyto_channels: list[np.ndarray],  # pass a list of image arrays, e.g. [cyto_647, cyto_488, ...]
    gui
):
    """
    Segments using nucleus + up to 2 cytoplasm channels
    Returns the same mask list for all cytoplasm channels
    """
    logger.info("Starting segmentation (Fish.predict) ...")

    # Pick first and second available cytoplasm channels -- TODO think of a more robust way to choose cytoplasm channel that works best for cellpose-sam
    cyto_imgs = [c for c in cyto_channels if c is not None]
    if not cyto_imgs or nucleus_img is None:
        logger.warning("Segmentation aborted: missing nucleus or cytoplasm channel")
        return [[] for _ in cyto_channels]
    cyto1 = cyto_imgs[0]
    cyto2 = cyto_imgs[1] if len(cyto_imgs) > 1 else np.zeros_like(cyto1)
    img = np.stack([nucleus_img, cyto1, cyto2], axis=-1).astype(np.float32, copy=False) # Stack as (H, W, 3): nucleus, cyto1, cyto2
    logger.debug(f"Fish.predict input shape={img.shape} dtype={img.dtype}")

    # Predict the masks using cellpose-sam 
    try:
        fish_model = gui.getBackEnd()
        masks, flows = fish_model.predict(img)  # defined in fishCore.py
    except Exception as e:
        logger.exception(f"Predict failed: {e}")
        return [[] for _ in cyto_channels]
    
    seg_objs = _masks_to_segments(masks, gui)   # convert each mask numpy array to segment object (defined in gui/canvas/segment.py)

    return [seg_objs for _ in cyto_channels]    # Return the same masks for all cytoplasm channels