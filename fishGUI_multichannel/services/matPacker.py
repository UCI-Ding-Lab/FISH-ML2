import pathlib
import numpy as np
import scipy.io

def read(mat: dict, img_number: int, target: str, cell: int, title: str):
    """
    Read one value back from the exported MATLAB structure.
    """
    if target == "filename":
        return mat["Tracked"][0, img_number]["filename"][0, 0]
    # dirname exists only on the first entry (if written)
    if target == "dirname":
        first = mat["Tracked"][0, 0]
        dtype = first.dtype
        if dtype is not None and dtype.names and ("dirname" in dtype.names):
            return first["dirname"][0, 0]
        return None
    return mat["Tracked"][0, img_number][target][0, 0][0, cell][title][0, 0]

def create(
    name: list[str],
    xy: list[list[tuple[float, float]]],
    masks: list[list[np.ndarray]],
    nucleus_masks: list[list[np.ndarray]],
    saveFile: pathlib.Path,
    dirname: str = None,
):
    """
    Build the MATLAB Tracked structure for every exported image entry.
    """
    tracked_dtype_head = np.dtype([
        ("filename", "O"),
        ("cells", "O"),
        ("dirname", "O"),
    ])
    tracked_dtype_tail = np.dtype([
        ("filename", "O"),
        ("cells", "O"),
    ])      

    cell_dtype = np.dtype([
        ('mask', 'O'),
        ('nucleus_mask', 'O'),
        ('pos', 'O'),
        ('size', 'O'),
        ('progenitor', 'O'),
        ('descendants', 'O'),
        ('Fmask', 'O'),
        ('area', 'O'),
        ('Acom', 'O'),
        ('Fpixels', 'O'),
        ('Ftotal', 'O'),
        ('Fmax', 'O'),
        ('Fmean', 'O')
    ])

    imgCount = len(name)
    tracked = np.empty((1, imgCount), dtype="O")

    for eachImg in range(imgCount):
        cellCount = len(xy[eachImg])
        cells = np.empty((1, cellCount), dtype="O")
        for eachCell in range(cellCount):
            cells[0, eachCell] = build_cell_data(
                cell_dtype,
                masks[eachImg][eachCell],
                nucleus_masks[eachImg][eachCell],
                xy[eachImg][eachCell],
            )

        # dirname only for the first entry
        if eachImg == 0:
            entry = np.zeros((1, 1), dtype=tracked_dtype_head)
            entry[0, 0]["dirname"] = np.array([[dirname if dirname else ""]], dtype="O")
        else:
            entry = np.zeros((1, 1), dtype=tracked_dtype_tail)

        entry[0, 0]["filename"] = np.array([[name[eachImg]]], dtype="O")
        entry[0, 0]["cells"]    = cells
        tracked[0, eachImg] = entry

    saveFile = pathlib.Path(saveFile)
    saveFile.parent.mkdir(parents=True, exist_ok=True)
    scipy.io.savemat(saveFile, {"Tracked": tracked})


def build_cell_data(cell_dtype, cyto_mask: np.ndarray, nucleus_mask: np.ndarray, xy: tuple[float, float]):
    """
    Build one exported MATLAB cell entry with paired cytoplasm and nucleus masks.
    """
    cell_data = np.zeros((1, 1), dtype=cell_dtype)
    cell_data[0, 0]["mask"] = cyto_mask.astype(np.double)
    cell_data[0, 0]["nucleus_mask"] = nucleus_mask.astype(np.double)
    cell_data[0, 0]["pos"] = np.array(xy).T.astype(np.double)
    cell_data[0, 0]["size"] = np.array([cyto_mask.shape[0], cyto_mask.shape[1]], dtype=np.double)
    cell_data[0, 0]["area"] = np.array([np.sum(cyto_mask)])
    fill_default_cell_fields(cell_data)
    return cell_data


def fill_default_cell_fields(cell_data) -> None:
    """
    Fill the legacy MATLAB fields that are not part of this segmentation step.
    """
    cell_data[0, 0]["progenitor"] = np.array([], dtype='O')
    cell_data[0, 0]["descendants"] = np.array([], dtype='O')
    cell_data[0, 0]["Fmask"] = np.zeros((0, 0))
    cell_data[0, 0]["Acom"] = np.array([np.nan])
    cell_data[0, 0]["Fpixels"] = np.array([], dtype='O')
    cell_data[0, 0]["Ftotal"] = np.array([0])
    cell_data[0, 0]["Fmax"] = np.array([0])
    cell_data[0, 0]["Fmean"] = np.array([0])
