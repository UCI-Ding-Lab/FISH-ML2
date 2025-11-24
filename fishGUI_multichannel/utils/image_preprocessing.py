import cv2
import numpy as np
from skimage import filters, morphology, segmentation

# TODO - grayscale to rgb is good for display/inference; helper__hdr2Rgb is good for finetuning ml models - look more into it
def grayscale_to_rgb(grayscale_img) -> np.ndarray:
    img_normalized = cv2.normalize(grayscale_img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    img_rgb = cv2.cvtColor(img_normalized, cv2.COLOR_GRAY2RGB)
    brightness_factor = 1
    return np.clip(img_rgb * brightness_factor, 0, 255).astype(np.uint8)

def normalize_to_uint8(img):
    return cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

def preprocess_nucleus_stack(stack: np.ndarray) -> np.ndarray:
    stack = stack[np.any(stack > 0, axis=(1, 2))]
    zprojected = np.max(stack, axis=0)
    return normalize_to_uint8(zprojected)

def preprocess_cytoplasm_stack(stack: np.ndarray, top_n: int = 8) -> np.ndarray:
    stack = stack[np.any(stack > 0, axis=(1, 2))]
    scores = [cv2.Laplacian(s, cv2.CV_64F).var() for s in stack]
    best_z = np.argsort(scores)[-top_n:]
    best_z.sort()
    zprojected = np.max(stack[best_z], axis=0)
    zprojected_normalized = normalize_to_uint8(zprojected)
    return zprojected_normalized

def clahe(img, clip_limit=4.0, tile_size=(8, 8)):
    c = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_size)
    return c.apply(img)

@staticmethod
def remove_outliers(img, k=18.0, use_median=False, verbose=False, max_clip_frac=1e-2):
    """
    Clip values that are more than k std-dev (or MAD units) above center.
    Args:
        img: 16-bit numpy array
        k: threshold (e.g. 3σ)
        use_median: if True use median+MAD, else mean+std
    Returns:
        clipped float32 image in [0,1]
    """

    print("OUTLIERS REMOVING...")
    x = img.astype(np.float32)

    if use_median:
        med = np.median(x)
        mad = np.median(np.abs(x - med)) + 1e-6
        sigma = 1.4826 * mad  # robust std estimate
        thresh = med + k * sigma
    else:
        mean = np.mean(x)
        std = np.std(x)
        thresh = mean + k * std

    # ---- Compute how many pixels would be clipped ----
    mask = x > thresh
    clip_frac = mask.mean()  # between 0 and 1

    if verbose:
        print(
            f"Threshold={thresh:.3f}, "
            f"clip_frac={clip_frac*100:.5f}% (max allowed={max_clip_frac*100:.5f}%)"
        )

    # ---- Decide whether to actually clip ----
    if (clip_frac == 0) or (clip_frac > max_clip_frac):
        # Either nothing to clip, or "too many" pixels above thresh
        # -> treat as no extreme outliers and skip clipping
        if verbose:
            if clip_frac == 0:
                print("No pixels above threshold — skipping outlier clipping.")
            else:
                print("Too many pixels above threshold — likely real signal, skipping clipping.")
        x_clipped = x
    else:
        # safe to treat as extreme outliers
        x_clipped = np.minimum(x, thresh)

    # ---- Normalize after clipping (to 0..1) ----
    x_min = x_clipped.min()
    x_max = x_clipped.max()
    x_norm = (x_clipped - x_min) / (x_max - x_min + 1e-6)
    return x_norm

def gradient(img: np.ndarray, ksize: int = 5) -> np.ndarray:
        kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
        return cv2.morphologyEx(img, cv2.MORPH_GRADIENT, kern)

def postproc_mask(m):
    m = morphology.remove_small_objects(m.astype(bool), min_size=200)
    m = morphology.binary_opening(m, footprint=morphology.disk(2))
    return m.astype(np.uint8)

def mask_to_bbox(mask):
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return None
    return (xs.min(), ys.min(), xs.max(), ys.max())
