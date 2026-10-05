import numpy as np
import scipy.io

from fishGUI_multichannel.services.mat_file_writer import build_cell_data, build_cell_dtype, write_tracked_mat_file


def read_first_cell_fields(mat_path):
    """Return the field names of the first exported cell."""
    mat = scipy.io.loadmat(mat_path)
    first_cell = mat["Tracked"][0, 0]["cells"][0, 0][0, 0]
    return first_cell.dtype.names


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


def test_build_cell_dtype_includes_nucleus_mask_only_when_requested():
    assert "nucleus_mask" in build_cell_dtype(True).names
    assert "nucleus_mask" not in build_cell_dtype(False).names
    assert build_cell_dtype(False).names[0] == "mask"


def test_build_cell_data_without_nucleus_mask_stores_only_mask():
    cyto_mask = np.array([[1, 1], [0, 1]])

    cell_data = build_cell_data(build_cell_dtype(False), cyto_mask, None, (5.0, 6.0))

    assert "nucleus_mask" not in cell_data.dtype.names
    assert np.array_equal(cell_data[0, 0]["mask"], cyto_mask.astype(np.double))
    assert np.array_equal(cell_data[0, 0]["size"], np.array([2, 2], dtype=np.double))


def test_write_tracked_mat_file_keeps_nucleus_mask_field_when_masks_are_given(tmp_path):
    mat_path = tmp_path / "paired.mat"
    mask = np.array([[1, 1], [1, 1]])

    write_tracked_mat_file(["img_w2-488_s001.tif"], [[(1, 1)]], [[mask]], [[mask]], mat_path)

    assert "nucleus_mask" in read_first_cell_fields(mat_path)


def test_write_tracked_mat_file_leaves_out_nucleus_mask_field_when_masks_are_none(tmp_path):
    mat_path = tmp_path / "single.mat"
    mask = np.array([[1, 1], [1, 1]])

    write_tracked_mat_file(["img_w2-488_s001.tif"], [[(1, 1)]], [[mask]], None, mat_path)

    fields = read_first_cell_fields(mat_path)
    assert "nucleus_mask" not in fields
    assert "mask" in fields
