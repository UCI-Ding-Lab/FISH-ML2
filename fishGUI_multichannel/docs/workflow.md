# FishGUI Intended Workflow

## Purpose

FishGUI Multichannel is a GUI for reviewing, segmenting, correcting, and exporting multichannel FISH/DAPI image samples.

The intended design is not just "run segmentation on one image."
It is a sample-based workflow where one biological sample may contain:

- one required DAPI image
- zero or more additional signal channels such as `647`, `488`, `555`, `594`, or `514`

The GUI should help the user move from raw imported TIFF files to cleaned, finalized masks that can be exported for downstream analysis.

---

## Main User Workflow

### 1. Import a folder of TIFF images

The user starts by clicking the import button and selecting a folder.

Expected behavior:

- load `.tif` images from the selected folder
- remember the selected import directory
- ignore non-TIFF files
- pass the TIFF files into the gallery-loading workflow
- automatically start bounding box generation after import finishes

Important intention:

- import is the entry point for a batch workflow
- import is not only about displaying files
- import should also trigger preprocessing steps needed for later segmentation

---

### 2. Group TIFF files into samples

The imported TIFF files should be grouped into samples using sample ID naming patterns.

Expected behavior:

- each sample represents one logical image set
- each sample should include one DAPI image as the required anchor image
- the same sample may also include extra channels such as `647`, `488`, `555`, `594`, `514`
- if a sample does not contain a DAPI image, skip that sample

Important intention:

- DAPI is the anchor image for a valid sample
- the GUI is sample-centered, not file-centered
- multichannel images belonging to the same sample should stay connected throughout the workflow

---

### 3. Create one gallery session per valid sample

After grouping, each valid sample should become one thumbnail/session object in the gallery.

Expected behavior:

- create one frame/session object for each valid sample
- attach the DAPI image and available extra channels to that sample
- add each session to the session pool
- update the channel menu based on the sample's available channels
- refresh the gallery scroll region
- focus the first valid sample automatically

Important intention:

- the gallery is the user's main way to navigate between samples
- the first usable sample should become active automatically to reduce friction

---

### 4. Auto-generate nucleus centers and DAPI masks in the background

After import, nucleus-center generation should start automatically for the session pool.

Expected behavior:

- run nucleus-center generation in the background
- segment DAPI nuclei while those centers are being prepared
- do not block the UI
- skip worker startup if the session pool is empty
- process each sample independently

Important intention:

- the UI should remain responsive during heavy computation
- center generation is a preparation step for segmentation
- DAPI segmentation should be ready before cytoplasm segmentation starts
- center generation should feel like part of import, not a separate manual task

---

### 5. Let the user click thumbnails to focus a sample

The user should be able to click any thumbnail to make that sample active.

Expected behavior:

- update which sample is focused
- update visual highlight state in the gallery
- sync the channel selector to the focused sample
- load the focused sample into the main image viewer
- clear or replace the previous loaded view as needed
- redraw the main viewer with the selected sample

Important intention:

- thumbnail click is the main navigation action
- the focused sample is the one the user is currently inspecting or editing

---

### 6. Support channel switching and mask display on the focused sample

The focused sample may have multiple channels, and the user should be able to switch between them.

Expected behavior:

- changing the channel selector updates the sample's current channel
- switching to `DAPI` shows the DAPI image
- switching to a cytoplasm channel shows that channel image
- the Display Masks toggle shows or hides the masks for the currently shown channel
- redraw the viewer using the selected channel's state
- keep segmentation data separated per channel

Important intention:

- segmentation is channel-aware
- masks for one channel should not silently overwrite another channel's masks
- the current channel controls which image and mask data the user sees and edits

---

### 7. Use selection mode to choose which samples remain in the working set

The user may import a large batch and only want to keep some samples for continued work.

Expected behavior:

- selection mode lets the user mark samples
- when selection mode is turned off, unselected samples can be removed from the active pool
- remaining thumbnails should return to the proper visual state
- the first remaining valid sample should be focused again

Important intention:

- selection mode is for pruning the batch
- this is an early workflow step before deeper segmentation work
- the user should be able to narrow the working set quickly

---

### 8. Use segmentation-selection mode to mark which samples should be segmented

There is a separate concept from general frame selection: a sample can be marked specifically for segmentation.

Expected behavior:

- samples can be toggled into a "selected for segmentation" state
- this state should be visually reflected
- turning the mode off should clear that state when appropriate
- only samples marked for segmentation should be sent into segmentation when the user runs it

Important intention:

- not every loaded sample should be segmented automatically
- the user needs control over which samples are processed

---

### 9. Run cytoplasm segmentation for selected samples

Once samples are marked for segmentation, the segmentation action should process them.

Expected behavior:

- only process samples marked for segmentation
- keep DAPI nucleus masks separate from cytoplasm masks
- segment every available cytoplasm channel for each selected sample
- store segmentation results under each matching cytoplasm channel
- show segmentation overlays only when Display Masks is active

Important intention:

- segmentation should respect both:
- which samples were selected for segmentation
- DAPI is a display and nucleus-reference channel, not a cytoplasm target
- segmentation results are part of the editable workflow, not always the final answer

---

### 10. Store segmentation separately for each channel

Each sample should manage segmentation lists independently per channel.

Expected behavior:

- `647` masks stay under `647`
- `488` masks stay under `488`
- changing channels swaps the active segmentation list
- one sample can have different masks for different channels
- the sample should know whether any segmentation exists and whether segmentation exists for a specific channel

Important intention:

- channel separation is a core design rule
- this should not be simplified into one global mask list per sample

---

### 11. Allow manual mask review and editing

After model output, the user should be able to manually inspect and refine masks.

Expected behavior:

- display segmentation patches on the canvas
- allow selecting a segment
- allow deleting a segment
- support edit history behavior such as undo/redo stacks if available
- redraw the viewer appropriately after edits

Important intention:

- manual correction is expected, not optional edge behavior
- model output is an initial draft, not always the final segmentation
- human-in-the-loop editing is part of the normal workflow

---

### 12. Copy one channel's mask to other channels

A major multichannel feature is the ability to reuse masks from one channel across other channels.

Expected behavior:

- the user selects a source channel
- the system ensures the source channel has segmentation
- if needed, generate segmentation for that source channel first
- extract finalized masks from the source channel
- apply those masks onto other target channels of the selected samples
- preserve the focused sample's selected channel after temporary processing
- update overlays when needed

Important intention:

- copy-channel-mask is a core multichannel workflow
- it is not just a convenience utility
- it exists because structural masks may be useful across channels for the same sample

---

### 13. Export finalized mask results

After review and cleanup, the user should be able to export.

Expected behavior:

- export should require a loaded image/sample
- use finalized mask data for output
- finalized mask data may come from edited segmentation results or applied channel masks
- export is the end of the workflow, after inspection and correction

Important intention:

- exported masks should represent cleaned, user-approved output
- export should happen after segmentation review, not before

---

## Short Workflow Summary

The intended high-level flow is:

`import folder -> group by sample -> require DAPI -> create sample sessions -> auto-generate centers and DAPI masks -> focus sample -> switch channel -> show or hide masks -> prune samples -> mark samples for segmentation -> run cytoplasm segmentation -> manually edit masks -> optionally copy one channel mask to other channels -> export finalized masks`

---

## Core Design Rules

Future changes should preserve these rules unless explicitly changed by the project owner.

### DAPI is required

A sample without DAPI is not considered valid for the main workflow.

### The workflow is sample-based

The GUI is built around one sample containing multiple related channels.

### Channel-specific masks must stay separate

Segmentation for `647` and `488` should not be mixed together by default.

### The UI should stay responsive

Long-running tasks like center generation, segmentation, or channel-mask copying should not freeze the interface.

### Manual editing is part of the intended user journey

Do not treat manual correction as unimportant or optional.

### Copy Channel Masks is a core feature

It reflects an important biological/multichannel workflow and should be preserved carefully.

### Export is the final step

The goal of the workflow is finalized masks ready for downstream use.

---

## Guidance For Future AI Assistants

When changing this project, assume the following unless the user says otherwise:

- Do not remove the requirement that samples are grouped around DAPI.
- Do not collapse per-channel segmentation into one shared segmentation list.
- Do not turn the app into a single-image-only workflow.
- Do not remove background processing for heavy tasks unless explicitly requested.
- Do not remove manual correction tools just because model automation exists.
- Do not treat copy-channel-mask as dead or secondary behavior.
- When changing UI logic, preserve the intended flow of:
  - import
  - sample grouping
  - gallery navigation
  - channel-aware segmentation
  - manual correction
  - export

If behavior seems unclear, prefer preserving:

- sample-based logic
- channel-aware logic
- human review/editing
- responsive background processing

---

## Known Product Intention In One Sentence

FishGUI Multichannel is intended to help a user load multichannel sample sets anchored by DAPI, generate and refine channel-aware segmentations, optionally propagate masks across channels, and export finalized masks for downstream analysis.
