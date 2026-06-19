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
    ) -> None:
        """
        Store one frame's masks in RLE form so the session can be restored later.
        """
        self.sample_id = sample_id 
        self.nucleus_path = nucleus_path
        self.cyto_paths = cyto_paths  
        self.bbox = np.array(bbox, dtype=np.uint16)
        self.rleNucleusSeg = encode_mask_list(nucleus_segment)
        self.rleSeg: dict[str, list[dict]] = {}
        for ch in segment:
            self.rleSeg[ch] = encode_mask_list(segment[ch])

    def extract_data_from_bundles(self) -> tuple:
        """
        Decode the saved masks back into numpy arrays for session loading.
        """
        segment_r = {}
        for ch in self.rleSeg:
            segment_r[ch] = decode_mask_list(self.rleSeg[ch])
        nucleus_segment_r = decode_mask_list(self.rleNucleusSeg)
        return self.sample_id, self.nucleus_path, self.cyto_paths, self.bbox.tolist(), segment_r, nucleus_segment_r


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
