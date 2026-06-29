# fishGUI_multichannel/gui Directory Overview

This directory contains all **graphical user interface components** for the multichannel FISH-ML application.

---

## abstract.py

**Core data model for one sample/frame**  
Loads and preprocesses DAPI and cytoplasm image data. Manages nucleus centers, DAPI nucleus masks, channel-specific cytoplasm masks, pairing results, and thumbnail states. Provides methods for selection, segmentation, channel switching, and export-ready state updates.

---

## frames.py

**Frame layout management**  
Defines subframes for organizing buttons, thumbnails, and canvas widgets. Provides methods to pack and access the layout containers used by the GUI.

---

## buttons.py

**Main workflow buttons and logic**  
Handles import, frame pruning, BBOX display, segmentation-frame selection, cytoplasm segmentation, mask display, source-mask copying, and export actions. Manages the current button states and triggers session-wide GUI updates.

Current main workflow buttons:

- `Import`
- `Select Frames`
- `BBOX`
- `Select Frames for Segmentation`
- `Segment`
- `Display Masks`
- `Apply Source Mask`
- `Export`

---

## toolbar.py

**Custom matplotlib toolbar**  
Extends `NavigationToolbar2Tk`, adds methods to reset tool states, and helps the GUI coordinate toolbar behavior with mask-editing tools.

---

## thumbnails.py

**Image gallery and sample grouping**  
Groups TIFF files into DAPI-anchored multichannel samples, creates gallery thumbnails, and updates their visual state as samples move through review and segmentation steps.

---

## tools_pannel.py

**Tool panel for mask editing and channel review**  
Provides brush, eraser, and add-box tools. Includes controls for marker size, contrast, brightness, save/load progress, and the channel selector. Handles switching between `DAPI` and cytoplasm channels while keeping the displayed masks synced to the selected channel.

---

## canvas/

### stove.py

**Main drawing canvas and image display**  
Integrates matplotlib with Tkinter. Handles image rendering, patch management, and mouse events for interaction. Redraws the current channel image and its active overlays when the user switches channels or toggles `BBOX` and `Display Masks`.

### box.py

**Bounding box annotation class**  
Handles drawing, selection, resizing, and anchor management for bounding boxes used in BBOX review and manual correction.

### segment.py

**Segmentation mask class**  
Handles mask drawing, selection, updating, undo/redo support, and deletion. Stores the patch used to display one nucleus or cytoplasm mask on the canvas.

### anchor.py

**Draggable anchor points for bounding boxes**  
Handles anchor drawing, selection, and color changes. Supports resizing and moving bounding boxes via direct manipulation on the canvas.

---

## How to Use

- Start the GUI via `python -m fishGUI_multichannel.app`.
- Import a folder of TIFF files that can be grouped into DAPI-anchored samples.
- Use the button row to prune samples, review BBOX results, choose frames for segmentation, display masks, and export results.
- Use the channel selector to switch between `DAPI` and available cytoplasm channels.
- Use the mask editor tools to refine the currently displayed mask set.
