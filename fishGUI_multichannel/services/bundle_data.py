from pycocotools import mask as maskUtils
import numpy as np
import pathlib
import base64

class bundle():
    """
    Pack one frame's bbox, nucleus masks, and cytoplasm masks for session save/load.
    """
    def __init__(
        self,
        sample_id,
        nucleus_path: pathlib.Path,
        cyto_paths: list[pathlib.Path],
        bbox: list[list],
        segment: dict[str, list[np.ndarray]],
        nucleus_segment: list[np.ndarray],
        selected_channel: str,
    ) -> None:
        """
        Store one frame's masks in RLE form so the session can be restored later.
        """
        self.sample_id = sample_id 
        self.nucleus_path = nucleus_path
        self.cyto_paths = cyto_paths  
        self.selected_channel = selected_channel
        self.bbox = np.array(bbox, dtype=float)
        self.rle_nucleus_masks = encode_mask_list(nucleus_segment)
        self.rle_cytoplasm_masks_by_channel: dict[str, list[dict]] = {}
        for ch in segment:
            self.rle_cytoplasm_masks_by_channel[ch] = encode_mask_list(segment[ch])

    def extract_data_from_bundles(self) -> tuple:
        """
        Decode the saved masks back into numpy arrays for session loading.
        """
        segment_r = {}
        cytoplasm_masks = get_saved_cytoplasm_masks_by_channel(self)
        for ch in cytoplasm_masks:
            segment_r[ch] = decode_mask_list(cytoplasm_masks[ch])
        nucleus_segment_r = decode_mask_list(get_saved_nucleus_masks(self))
        return (
            self.sample_id,
            self.nucleus_path,
            self.cyto_paths,
            self.bbox.tolist(),
            segment_r,
            nucleus_segment_r,
            get_saved_selected_channel(self),
        )


def get_saved_cytoplasm_masks_by_channel(bundle_obj) -> dict[str, list[dict]]:
    """
    Return the stored cytoplasm masks using either the new or legacy bundle field name.
    """
    if "rle_cytoplasm_masks_by_channel" in bundle_obj.__dict__:
        return bundle_obj.rle_cytoplasm_masks_by_channel
    return bundle_obj.rleSeg


def get_saved_nucleus_masks(bundle_obj) -> list[dict]:
    """
    Return the stored nucleus masks using either the new or legacy bundle field name.
    """
    if "rle_nucleus_masks" in bundle_obj.__dict__:
        return bundle_obj.rle_nucleus_masks
    return bundle_obj.rleNucleusSeg


def get_saved_selected_channel(bundle_obj) -> str:
    """
    Return the stored selected channel and fall back to the legacy default when missing.
    """
    if "selected_channel" in bundle_obj.__dict__:
        return bundle_obj.selected_channel
    return "647"


def encode_mask_list(mask_list: list[np.ndarray]) -> list[dict]:
    """
    Encode one list of binary masks into compact RLE dictionaries.
    """
    encoded_masks = []
    for mask in mask_list:
        data = maskUtils.encode(np.asfortranarray(mask))
        data["counts"] = base64.b64encode(data["counts"]).decode("utf-8")
        encoded_masks.append(data)
    return encoded_masks


def decode_mask_list(encoded_masks: list[dict]) -> list[np.ndarray]:
    """
    Decode one saved RLE mask list back into numpy mask arrays.
    """
    masks = []
    for data in encoded_masks:
        decoded = data.copy()
        decoded["counts"] = base64.b64decode(decoded["counts"].encode("utf-8"))
        masks.append(maskUtils.decode(decoded))
    return masks
