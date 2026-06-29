# FISH-ML: DAPI Cell Image Segmentation

FISH-ML is a unified framework for multichannel FISH and DAPI image review, segmentation, correction, and export. The current FishGUI multichannel workflow combines GroundingDINO-based nucleus-center proposals with Cellpose-SAM-based nucleus and cytoplasm segmentation so users can move from raw TIFF files to finalized masks.

---

## Dataset Preparation
For the current multichannel workflow, ensure that your images meet the following specifications:

- **Image dimensions:** `2048 x 2048 x 1`
- **Color space:** `16-bit grayscale`
- **Format:** `.tif`
- **Required anchor channel:** one `DAPI` image per sample
- **Optional signal channels:** `647`, `488`, `555`, `594`, `514`

---

## Environment Setup

### Initial Installation
Follow these steps to set up the environment for the first time. If you have already completed the setup, please do not overwrite your existing environment and proceed to the [Running FishMultichannelUI](#running-fishmultichannelui) section.

#### Conda Installation
You can install the necessary dependencies using the provided `env.yaml` file in Anaconda. Alternatively, follow these steps:

```bash
conda create -n fish python=3.11.7
conda activate fish
pip install -r requirements.txt
```

### Downloading Required Assets
The current multichannel GUI expects two groups of external files:

- shared GUI assets such as icons and optional sample TIFF folders
- the Cellpose-SAM checkpoint used for segmentation

The current Cellpose-SAM weights can be downloaded from the following link:
[Cellpose-SAM Weights Folder](https://drive.google.com/drive/folders/1PV2_K14ZOFsYIagmr0WM4Pg9eHKpSbBO?usp=sharing)

If you also need the older shared assets package, please request access via email: **shizukat@uci.edu**.

Once downloaded, organize the files in the root directory of the repository like this:

```text
/FISH-ML2  # Root directory
|-- /assets
|   |-- /icon
|   |   |-- brush.png
|   |   `-- eraser.png
|   `-- /model
|-- /cellpose-SAM
|   `-- /weights
|       `-- fish_cellpose_v1.pt
|-- /GroundingDINO
|-- /fishGUI_multichannel
|-- fishCore.py
|-- README.md
|-- requirements.txt
|-- env.yaml
|-- config.ini
...
```

---

## Installing Cellpose-SAM and Grounding DINO
To ensure seamless operation, the current multichannel GUI expects both a Cellpose-SAM checkpoint and GroundingDINO resources:

- **Cellpose-SAM weights:** [Google Drive Folder](https://drive.google.com/drive/folders/1PV2_K14ZOFsYIagmr0WM4Pg9eHKpSbBO?usp=sharing)
- **Cellpose-SAM checkpoint path:** `cellpose-SAM/weights/fish_cellpose_v1.pt`
- **Grounding DINO:** [GitHub Repository](https://github.com/IDEA-Research/GroundingDINO)
- **Grounding DINO Checkpoint:** [Hugging Face Model](https://huggingface.co/ShilongLiu/GroundingDINO/blob/main/groundingdino_swint_ogc.pth)

Once downloaded, ensure that they are placed in the following structure within your project:

```text
/FISH-ML  # Root directory
|-- /cellpose-SAM
|   `-- /weights
|       `-- fish_cellpose_v1.pt
|-- /GroundingDINO
|   |-- groundingdino
|   |   `-- weights
|   |       `-- groundingdino_swint_ogc.pth
|   ...
|-- /assets
|-- /fishGUI_multichannel
|-- README.md
|-- requirements.txt
|-- env.yaml
|-- config.ini
|-- fishCore.py
...
```

---

## Running FishMultichannelUI
After successfully setting up the environment and installing all required dependencies, you can launch **FishGUI Multichannel** using the following steps:

```bash
# Activate the environment
conda activate fish

# Run FishGUI
python -m fishGUI_multichannel.app
```

Once the script executes, a UI window will appear, allowing you to begin reviewing and segmenting multichannel image sets. The current multichannel GUI loads the Cellpose-SAM checkpoint from `cellpose-SAM/weights/fish_cellpose_v1.pt` and also loads GroundingDINO for nucleus-center proposals and BBOX review.

---

## Current FishGUI Workflow
The current FishGUI multichannel workflow is sample-based rather than file-based.

Expected workflow:

- import a folder of TIFF files
- group files into samples using the shared sample ID
- require one DAPI image per sample
- auto-generate nucleus centers and DAPI masks in the background during import
- keep the `BBOX` mode available for center and box review
- switch between `DAPI` and available cytoplasm channels on the focused sample
- use `Display Masks` to show the masks for the currently selected channel
- mark frames with `Select Frames for Segmentation`
- run `Segment` to segment every available cytoplasm channel for those selected frames
- use `Apply Source Mask` to copy one reviewed cytoplasm mask to other cytoplasm channels
- export finalized MATLAB output after review and correction

---

## Export Format
The current `integrate-DAPI` export path writes paired whole-cell and nucleus masks for each exported cell.

Each exported MATLAB cell entry can store:

- `mask`: cytoplasm or whole-cell segmentation
- `nucleus_mask`: matched nuclear segmentation for that same cell
- `pos`: exported cell position
- `size`: mask size metadata

The current export flow also writes filename metadata and can generate a pairing debug PDF when pairing data is available.

---

## Notes on Model Checkpoints
The current multichannel GUI loads the Cellpose-SAM checkpoint `fish_cellpose_v1.pt` for segmentation. The older SAM checkpoints listed below are kept as historical reference for earlier experiments and validation work.

| Checkpoint         | Epochs | Images | Patch Size | Overlap | Patches | Loss   |
|--------------------|--------|--------|------------|---------|---------|--------|
| `fish_v1.1.pth`    | 1      | 50     | 256        | 0.5     | 11,250  | 0.89   |
| `fish_v1.100.pth`  | 100    | 50     | 256        | 0.5     | 11,250  | 0.4655 |
| `fish_v2.1.pth`    | 1      | 150    | 256        | 0.5     | 33,750  | 0.63   |
| `fish_v3.50.pth`   | 50     | 150    | Whole Image Input | - | - | - |

Note: if you are running the current multichannel GUI, make sure the Cellpose-SAM checkpoint and GroundingDINO files are both in place.

---

## Future Enhancements
We are actively improving this repository and refining the multichannel GUI workflow, including export, pairing, and segmentation review behavior.

For any issues, feature requests, or contributions, feel free to open an issue or submit a pull request.

## License
This project is developed under [UCI Ding Lab](https://www.ding.eng.uci.edu).
