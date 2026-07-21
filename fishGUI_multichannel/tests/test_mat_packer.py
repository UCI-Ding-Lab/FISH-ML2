import numpy as np

from fishGUI_multichannel.services.matPacker import build_cell_data


def test_build_cell_data_stores_both_cytoplasm_and_nucleus_masks():
    cell_dtype = np.dtype([
        ("mask", "O"),
        ("nucleus_mask", "O"),
        ("pos", "O"),
        ("size", "O"),
        ("progenitor", "O"),
        ("descendants", "O"),
        ("Fmask", "O"),
        ("area", "O"),
        ("Acom", "O"),
        ("Fpixels", "O"),
        ("Ftotal", "O"),
        ("Fmax", "O"),
        ("Fmean", "O"),
    ])
    cyto_mask = np.array([[1, 0], [0, 1]])
    nucleus_mask = np.array([[0, 1], [1, 0]])

    cell_data = build_cell_data(cell_dtype, cyto_mask, nucleus_mask, (5.0, 6.0))

    assert np.array_equal(cell_data[0, 0]["mask"], cyto_mask.astype(np.double))
    assert np.array_equal(cell_data[0, 0]["nucleus_mask"], nucleus_mask.astype(np.double))
    assert np.array_equal(cell_data[0, 0]["size"], np.array([2, 2], dtype=np.double))
    assert cell_data[0, 0]["progenitor"].dtype == np.double
    assert cell_data[0, 0]["descendants"].dtype == np.double
