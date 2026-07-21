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

## export_pairs.py

**Export pairing data collection**  
Collects the matched cytoplasm masks, matched nucleus masks, and exported cell positions for one channel before MATLAB export.

---

## matPacker.py

**MATLAB export structure builder**  
Builds the `Tracked` MATLAB structure written during export. In the current `integrate-DAPI` workflow, each exported cell entry stores both:

- `mask`: cytoplasm or whole-cell segmentation
- `nucleus_mask`: matched nuclear segmentation

---

## progress.py

**Save, load, and export entry points**  
Handles saving session progress to `.pkl`, loading saved sessions back into the GUI, and exporting finalized MATLAB results plus optional pairing debug output.

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
- `pairing.py`, `export_pairs.py`, and `matPacker.py` prepare the paired cytoplasm and nucleus data used for export.
- `progress.py` is the main entry point for save, load, and export behavior.
