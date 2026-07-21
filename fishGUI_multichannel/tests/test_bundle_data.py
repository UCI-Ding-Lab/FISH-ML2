import numpy as np

from fishGUI_multichannel.services.bundle_data import bundle


def test_bundle_round_trip_preserves_nucleus_and_cytoplasm_masks():
    nucleus_mask = np.array([[1, 0], [0, 1]], dtype=np.uint8)
    cytoplasm_mask = np.array([[0, 1], [1, 0]], dtype=np.uint8)
    bundled = bundle(
        "sample-1",
        nucleus_path="nucleus.tif",
        cyto_paths=["cyto_647.tif"],
        bbox=[[1, 2, 3, 4]],
        segment={"647": [cytoplasm_mask]},
        nucleus_segment=[nucleus_mask],
    )

    sample_id, nucleus_path, cyto_paths, bbox, seg_dict, nucleus_segments = bundled.extract_data_from_bundles()

    assert sample_id == "sample-1"
    assert nucleus_path == "nucleus.tif"
    assert cyto_paths == ["cyto_647.tif"]
    assert bbox == [[1, 2, 3, 4]]
    assert np.array_equal(seg_dict["647"][0], cytoplasm_mask)
    assert np.array_equal(nucleus_segments[0], nucleus_mask)
