# fishGUI_multichannel/services Directory Overview

This directory contains the **non-UI workflow logic** for the multichannel FISH-ML application. These files handle background session work, segmentation, pairing, save/load behavior, and MATLAB export.

---

## session_manager.py

**Session-wide workflow coordination**  
Manages the active pool of samples, focused-frame state, background worker startup, segmentation selection, segmentation timing export, and batch actions such as copied-mask application.

---

## segmentation.py

**Model inference helpers**  
Runs nucleus segmentation from the DAPI image and cytoplasm segmentation for the selected signal channel. Prepares model inputs and converts model masks into GUI segment objects.

---

## apply_channel_mask.py

**Copy one reviewed cytoplasm mask across channels**  
Handles the background workflow for reusing one source cytoplasm mask on other cytoplasm channels and frames. Preserves channel-aware state and refreshes overlays when needed.

---

## pairing.py

**Nucleus-to-cytoplasm pairing logic**  
Builds pairings between DAPI nucleus masks and cytoplasm masks for each channel. Also generates the optional pairing debug PDF used to inspect matched and unmatched results.

---

## export_modes.py

**Export mode choices**  
Defines the three export modes and their popup labels, decides which modes are available for the selected frames, and picks the mode the popup starts on.

---

## export_cell_data.py

**Export cell data collection**  
Builds the cell positions and cropped masks for one frame before MATLAB export: paired whole-cell and nucleus masks, nucleus masks only, or whole-cell masks only.

---

## mat_file_writer.py

**MATLAB export structure builder**  
Builds and writes the `Tracked` MATLAB structure during export (`write_tracked_mat_file`). Each exported cell entry stores:

- `mask`: always present; the mask DoFISH analyzes
- `nucleus_mask`: only present when nucleus masks are passed in (paired export); otherwise the field is left out, matching older DoFISH files

---

## session_save_load.py

**Save and load entry points**  
Handles saving session progress to `.pkl` and loading saved sessions back into the GUI.

---

## mat_export.py

**MATLAB export entry point**  
Runs the export from start to finish for the chosen export mode: asks for the `.mat` path, collects cell data for each selected frame, writes the MATLAB file, writes the optional pairing debug output (paired mode only), and warns about selected frames that ended up with no cells.

---

## bundle_data.py

**Session serialization helpers**  
Packages bounding boxes, cytoplasm masks, and nucleus masks into a saveable bundle representation so sessions can be restored later.

---

## __init__.py

**Package marker**  
Marks the services directory as a Python package.

---

## How to Use

- `session_manager.py` coordinates sample-level background work across the whole GUI.
- `segmentation.py` and `apply_channel_mask.py` provide the main heavy workflow actions.
- `pairing.py`, `export_cell_data.py`, and `mat_file_writer.py` prepare the cell data used for export.
- `session_save_load.py` is the main entry point for save and load behavior.
- `mat_export.py` is the main entry point for MATLAB export.
- `export_modes.py` decides which export modes are offered and which one the popup starts on.
