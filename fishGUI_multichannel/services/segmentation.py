import numpy as np
from skimage import filters, morphology, segmentation
from skimage.restoration import estimate_sigma
from scipy import ndimage as ndi
import cv2
import logging
import time

from ..gui.canvas.segment import segment
from ..utils.image_preprocessing import (
    remove_outliers,
    normalize_to_uint8,
    clahe,
    postproc_mask,  
    gradient,
    mask_to_bbox       
)

logger = logging.getLogger(__name__)

def watershed_segment_with_centers(cyt_img: np.ndarray,
                                    centers: list[tuple[float,float]]
                                    ) -> list[np.ndarray]:
    """
    Segment cytoplasm with image using watershed, seeded at the nucleus center
    Returns a list of binary masks. 
    """
    thresh = filters.threshold_otsu(cyt_img)
    binary = cyt_img > thresh
    binary = morphology.remove_small_holes(cyt_img > thresh, area_threshold=1000)
    binary = morphology.remove_small_objects(binary, min_size=1000)
    dist   = ndi.distance_transform_edt(binary)

    markers = np.zeros(cyt_img.shape, np.int32)
    for i,(cx,cy) in enumerate(centers, start=1):
        xi, yi = int(round(cx)), int(round(cy))
        if 0 <= yi < cyt_img.shape[0] and 0 <= xi< cyt_img.shape[1]:
            markers[yi, xi] = i

    elev = -dist + 5 * (filters.sobel(cyt_img))
    labels = segmentation.watershed(elev, markers=markers, mask=binary)

    masks = []
    for i in range(1, np.max(labels)+1):
        mask = (labels == i)
        if np.sum(mask) > 0:
            masks.append(postproc_mask(mask))
    return masks

def bbox_run_basic_watershed(
    nucleus_img: np.ndarray,
    cyto_imgs: dict[str, np.ndarray],
    gui,
    selected_channel: str,
    bbox_mode = False,
    seg_mode = False
) -> tuple[list[segment], list[segment]]:
    """
    Build one bbox set for the frame using a single cytoplasm channel.

    Channel selection priority:
    1) selected_channel (if available)
    2) fallback order: 647, 488, 555, 594, 514, undocumented channel
    """

    boxes = gui.getBackEnd().AppIntDINOwrapper(nucleus_img)
    centers = [((x0 + x1) / 2, (y0 + y1) / 2) for x0, y0, x1, y1 in boxes]

    proc = None
    channel_priority = [selected_channel, "647", "488", "555", "594", "514"]
    for channel in channel_priority:
        if not channel:
            continue

        image = cyto_imgs.get(channel)

        if image is None:
            continue
        if proc is not None:
            # Found a valid channel to use for bbox generation
            break

        if channel == "647" or channel not in {"488", "594", "555", "514"}: # chan == 647 or undocumented channel
            proc = image

        else:  # chan == "488, 594, 555, 514"
            cyt_clahe = image
            sigma_est = estimate_sigma(image) # Calculate sigma
            sigma_norm = sigma_est + 3.0
            sigma_weak = sigma_est - 10.0

            cyt_bilat = cv2.bilateralFilter(cyt_clahe, d=9, sigmaColor=sigma_norm, sigmaSpace=15, borderType=cv2.BORDER_REFLECT_101)
            cyt_edge_preserved = cv2.edgePreservingFilter(cyt_clahe, flags=1, sigma_s=sigma_norm, sigma_r=0.4)
            cyt_bilat_edge = cv2.edgePreservingFilter(cyt_bilat, flags=1, sigma_s=sigma_weak, sigma_r=0.4)

            laplacian = cv2.Laplacian(image, cv2.CV_64F)
            laplacian = cv2.convertScaleAbs(laplacian)

            proc = cyt_bilat_edge


    ws_masks = watershed_segment_with_centers(proc, centers) 
    bboxes = [mask_to_bbox(m) for m in ws_masks]
    bboxes = [b for b in bboxes if b is not None]
    bboxes = [
        [float(x1), float(y1), float(x2), float(y2)] 
        for (x1, y1, x2, y2) in bboxes
    ]

    return bboxes
        
def run_basic_watershed(
    nucleus_img: np.ndarray,
    cyto_647: np.ndarray,
    cyto_488: np.ndarray,
    cyto_555: np.ndarray,
    cyto_594: np.ndarray,
    cyto_514: np.ndarray,
    gui,
    selected_channel: str
) -> tuple[list[segment], list[segment]]:
    """
    Perform segmentation for both channels and return (seg_647, seg_488)
    """
    start = time.time()
    boxes = gui.getBackEnd().AppIntDINOwrapper(nucleus_img)
    centers = [((x0 + x1) / 2, (y0 + y1) / 2) for x0, y0, x1, y1 in boxes]

    # process 647 first (cyto1), then 488 (cyto2)
    # TODO - O(n^2) -- consider improving time complexity
    seg_647, seg_488, seg_555, seg_594, seg_514 = [], [], [], [], []
    channels_images = {
        "647": cyto_647,
        "488": cyto_488,
        "555": cyto_555,
        "594": cyto_594,
        "514": cyto_514
    }
    for channel, image in channels_images.items():
        if image is None:
            continue

        if channel == "647": 
            grad  = gradient(image, ksize=5)
            proc = image
            rgb  = np.stack([image, image, grad], axis=-1)

        else:  # chan == "488, 594, 555, or 514"
            sigma_est = estimate_sigma(image, channel_axis=None, average_sigmas=True)
            sigma_norm = sigma_est + 3.0
            sigma_weak = sigma_est - 10.0

            cyt_bilat = cv2.bilateralFilter(image, d=9, sigmaColor=sigma_norm, sigmaSpace=15, borderType=cv2.BORDER_REFLECT_101)
            cyt_edge_preserved = cv2.edgePreservingFilter(image, flags=1, sigma_s=sigma_norm, sigma_r=0.4)
            cyt_bilat_edge = cv2.edgePreservingFilter(cyt_bilat, flags=1, sigma_s=sigma_weak, sigma_r=0.4)

            laplacian = cv2.Laplacian(image, cv2.CV_64F)
            laplacian = cv2.convertScaleAbs(laplacian)
            cyt_blended = cv2.addWeighted(cyt_bilat, 0.8, laplacian, 0.2, 0)

            proc = cyt_bilat_edge
            rgb  = np.stack([cyt_blended, cyt_bilat, cyt_edge_preserved], axis=-1)

        ws_masks = watershed_segment_with_centers(proc, centers) 
        bboxes = [mask_to_bbox(m) for m in ws_masks]
        bboxes = [b for b in bboxes if b is not None]

        channel_masks = []
        for bb in bboxes:
            try:
                box_input = [[[float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])]]]
                sets = gui.getBackEnd().finetune.AppIntPREDICTCytoplasmWrapper(rgb, box_input)
                if sets is not None and len(sets) > 0 and sets[0] is not None and len(sets[0]) > 0:
                    best = max(sets[0], key=lambda m: m.sum())
                    channel_masks.append(postproc_mask(best))
            except Exception as e:
                logger.error(f"SAM refine failed on {channel} box {bb}: {str(e)}")

        seg_objs = [segment(gui, m) for m in channel_masks]
        
        if channel == "647":
            seg_647 = seg_objs
        elif channel == "488":
            seg_488 = seg_objs
        elif channel == "555":
            seg_555 = seg_objs
        elif channel == "594":
            seg_594 = seg_objs
        elif channel == "514":
            seg_514 = seg_objs
    
    end = time.time()
    logger.info(f"Segmentation completed in {end - start:.2f} seconds")
        
    return seg_647, seg_488, seg_555, seg_594, seg_514