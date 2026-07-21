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
- automatically start nucleus center and prompt-box preparation after import finishes

Important intention:

- import is the entry point for a batch workflow
- import is not only about displaying files
- import should also trigger preprocessing steps needed for later nucleus and cytoplasm workflows

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

### 4. Auto-generate nucleus centers and prompt boxes in the background

After import, nucleus center preparation should start automatically for the session pool.

Expected behavior:

- run nucleus center and prompt-box preparation in the background
- do not block the UI
- skip worker startup if the session pool is empty
- process each sample independently
- show the prepared state on thumbnails with the purple status overlay

Important intention:

- the UI should remain responsive during heavy computation
- nucleus center preparation is the gating step before later nucleus and cytoplasm work
- import should prepare prompt boxes without forcing nucleus segmentation immediately
- this preparation should feel like part of import, not a separate manual task

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
- the red border should make the active sample obvious

---

### 6. Support channel switching on the focused sample

The focused sample may have multiple channels, and the user should be able to switch between them.

Expected behavior:

- changing the channel selector updates the sample's current channel
- switching to `DAPI` shows the DAPI image
- switching to a cytoplasm channel shows that channel image
- redraw the viewer using the selected channel's state
- keep segmentation data separated per channel

Important intention:

- segmentation is channel-aware
- masks for one channel should not silently overwrite another channel's masks
- the current channel controls which image and mask data the user sees and edits

---

### 7. Use `Select Frames` to choose which samples remain in the working set

The user may import a large batch and only want to keep some samples for continued work.

Expected behavior:

- turning `Select Frames` on lets the user mark thumbnails for removal
- selected frames remain in the pool
- turning `Select Frames` off removes the thumbnails marked with the red cross
- remaining thumbnails should return to the proper visual state
- the first remaining valid sample should be focused again

Important intention:

- `Select Frames` is for pruning the batch
- this is an early workflow step before deeper segmentation work
- the user should be able to narrow the working set quickly

---

### 8. Enter nucleus workflow with `Segment Nucleus`

Nucleus segmentation is a separate workflow from cytoplasm segmentation.

Expected behavior:

- clicking `Segment Nucleus` prompts the user to choose a nucleus backend
- the available nucleus backends are `Cellpose-SAM` and `GroundingDINO + SAM`
- once chosen, all loaded frames switch to the `DAPI` channel
- the toolbar changes to the nucleus-specific controls for the selected backend

Important intention:

- nucleus work is intentionally split from cytoplasm work
- `DAPI` is the nucleus review and segmentation channel
- the nucleus workflow should feel explicit rather than hidden inside the general segmentation action

---

### 9. Support nucleus review and segmentation for the chosen backend

The nucleus workflow should reflect the backend the user selected.

Expected behavior:

- for `GroundingDINO + SAM`, `BBOX` review should be available
- for `GroundingDINO + SAM`, the user can review, adjust, delete, and add prompt boxes before segmentation
- for `Cellpose-SAM`, nucleus segmentation should run without bbox review
- pressing `Segment` in nucleus workflow should segment nuclei for all loaded frames
- generated nucleus masks should be reflected on thumbnails with the blue status overlay

Important intention:

- `GroundingDINO + SAM` remains valuable because prompt review is part of the nucleus workflow
- `Cellpose-SAM` remains the simpler direct nucleus workflow
- both nucleus paths should still end in stored DAPI nucleus masks

---

### 10. Use `Display/Edit` for mask review and manual correction

After model output, the user should be able to inspect and refine masks.

Expected behavior:

- `Display/Edit` shows masks for the currently focused sample and current channel
- when the current channel is `DAPI`, `Display/Edit` shows nucleus masks
- when the current channel is a cytoplasm channel, `Display/Edit` shows cytoplasm masks for that channel
- the user can select a mask, edit it with brush or eraser, add a new mask, or delete the selected mask
- undo, redo, and reset shortcuts should apply to mask editing

Important intention:

- manual correction is expected, not optional edge behavior
- model output is an initial draft, not always the final segmentation
- human-in-the-loop editing is part of the normal workflow

---

### 11. Enter cytoplasm workflow with `Segment Cytoplasm`

Cytoplasm segmentation is its own workflow mode.

Expected behavior:

- clicking `Segment Cytoplasm` switches the UI into cytoplasm workflow mode
- the focused frame should switch to its first available non-DAPI channel
- the cytoplasm toolbar should expose `Select Cytoplasm Frames`, `Segment All Channels for Selected Frames`, `Copy Best Channel Mask to All Frames`, and `Display/Edit`

Important intention:

- cytoplasm work should happen on non-DAPI channels
- the user should see a clear mode change before running cytoplasm actions

---

### 12. Use `Select Cytoplasm Frames` to choose which samples should be segmented

There is a separate concept from general frame selection: a sample can be marked specifically for cytoplasm segmentation.

Expected behavior:

- samples can be toggled into a "selected for segmentation" state
- this state should be visually reflected on thumbnails
- only frames with prepared nucleus centers and prompt boxes should be selectable for cytoplasm segmentation
- only samples marked for cytoplasm segmentation should be sent into batch cytoplasm segmentation

Important intention:

- not every loaded sample should be segmented automatically
- the user needs control over which samples are processed
- cytoplasm selection depends on earlier nucleus preparation being complete

---

### 13. Run cytoplasm segmentation for selected samples

Once samples are marked for cytoplasm segmentation, the segmentation action should process them.

Expected behavior:

- only process samples marked for segmentation during batch mode
- segment every available cytoplasm channel for each selected sample
- store segmentation results under each matching cytoplasm channel
- keep DAPI nucleus masks separate from cytoplasm masks
- show the completed cytoplasm state on thumbnails with the orange status overlay
- if no samples were marked first, the focused frame can still be segmented for its current cytoplasm channel

Important intention:

- cytoplasm segmentation should respect explicit user selection when batch mode is used
- DAPI is a display and nucleus-reference channel, not a cytoplasm target
- segmentation results are part of the editable workflow, not always the final answer

---

### 14. Store segmentation separately for each channel

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

### 15. Copy one channel's mask to other cytoplasm channels and frames

A major multichannel feature is the ability to reuse one cytoplasm mask across other cytoplasm channels.

Expected behavior:

- the user selects a source cytoplasm channel
- the system ensures the source channel has segmentation
- if needed, generate segmentation for that source channel first
- extract finalized masks from the source channel
- apply those masks onto cytoplasm target channels across the chosen frames
- preserve the focused sample's selected channel after temporary processing
- update overlays when needed

Important intention:

- copied cytoplasm masks are a core multichannel workflow
- it is not just a convenience utility
- it exists because structural masks may be useful across channels for the same sample
- `DAPI` should not be treated as a source channel for this feature

---

### 16. Export finalized mask results

After review and cleanup, the user should be able to export.

Expected behavior:

- export should require at least one loaded sample
- export should include all currently loaded frames
- export should iterate through all available cytoplasm channels for each loaded frame
- finalized mask data may come from edited segmentation results or applied channel masks
- the export step is the end of the workflow, after inspection and correction

Important intention:

- exported masks should represent cleaned, user-approved output
- export should happen after segmentation review, not before
- the workflow is designed around review first and output second

---

## Short Workflow Summary

The intended high-level flow is:

`import folder -> group by sample -> require DAPI -> create sample sessions -> auto-generate nucleus centers and prompt boxes -> focus sample -> switch channels -> prune frames -> enter nucleus workflow -> review boxes when using GroundingDINO + SAM -> segment nuclei for all loaded frames -> use Display/Edit for review and correction -> enter cytoplasm workflow -> mark cytoplasm frames -> segment all cytoplasm channels for selected frames -> optionally copy one cytoplasm channel mask to other cytoplasm channels -> export finalized masks`

---

## Core Design Rules

Future changes should preserve these rules unless explicitly changed by the project owner.

### DAPI is required

A sample without DAPI is not considered valid for the main workflow.

### The workflow is sample-based

The GUI is built around one sample containing multiple related channels.

### Nucleus and cytoplasm workflows stay separate

The GUI should preserve the explicit split between `Segment Nucleus` and `Segment Cytoplasm`.

### Nucleus workflow stays DAPI-centered

The nucleus workflow should switch frames to `DAPI`, support the selected nucleus backend, and store nucleus masks separately from cytoplasm masks.

### Channel-specific masks must stay separate

Segmentation for `647` and `488` should not be mixed together by default.

### The UI should stay responsive

Long-running tasks like center generation, segmentation, or channel-mask copying should not freeze the interface.

### Manual editing is part of the intended user journey

Do not treat manual correction as unimportant or optional.

### Copy Channel Masks is a core feature

It reflects an important biological/multichannel workflow and should be preserved carefully.

### Thumbnail status indicators matter

The thumbnail overlays communicate processing state and should remain meaningful:

- purple for prepared nucleus centers or prompts
- blue for stored nucleus masks
- orange for completed cytoplasm segmentation across channels

### Export is the final step

The goal of the workflow is finalized masks ready for downstream use.

---

## Guidance For Future AI Assistants

When changing this project, assume the following unless the user says otherwise:

- Do not remove the requirement that samples are grouped around DAPI.
- Do not merge the nucleus and cytoplasm workflows into one ambiguous segmentation flow.
- Do not remove the nucleus backend choice between `Cellpose-SAM` and `GroundingDINO + SAM`.
- Do not remove `BBOX` review from the `GroundingDINO + SAM` nucleus path unless explicitly requested.
- Do not collapse per-channel segmentation into one shared segmentation list.
- Do not turn the app into a single-image-only workflow.
- Do not remove background processing for heavy tasks unless explicitly requested.
- Do not remove manual correction tools just because model automation exists.
- Do not treat copy-channel-mask as dead or secondary behavior.
- When changing UI logic, preserve the intended flow of:
  - import
  - sample grouping
  - gallery navigation
  - nucleus workflow selection
  - `DAPI`-centered nucleus review and segmentation
  - cytoplasm workflow selection
  - channel-aware cytoplasm segmentation
  - manual correction
  - export

If behavior seems unclear, prefer preserving:

- sample-based logic
- explicit nucleus-versus-cytoplasm workflow separation
- channel-aware logic
- human review/editing
- responsive background processing
- status feedback through thumbnail overlays

---

## Known Product Intention In One Sentence

FishGUI Multichannel is intended to help a user load multichannel sample sets anchored by DAPI, prepare nucleus prompts, segment nuclei and cytoplasm through separate but connected workflows, refine channel-aware masks, optionally propagate cytoplasm masks across channels, and export finalized masks for downstream analysis.
