# Project TODOs

- High priority: Clarify MATLAB export behavior and DoFISH compatibility
  - Before August 17, export created an entry for every cytoplasm channel per sample; the August change exports only the first channel
  - Review whether DoFISH needs one shared cell-mask set per sample or separate masks for each cytoplasm channel
  - Decide which mask should be exported when channels have different segmentation results; the current first channel is not necessarily the selected or best channel
  - Compare old and current exports in DoFISH using a multichannel sample to check frame counts, cell matching, and DAPI nucleus masks
  - Update export code, documentation, and tests after confirming the intended behavior; current tests describe existing behavior rather than validate the design
  - Export modes (nucleus only, whole-cell only, paired) were added; confirm with Dr. Ding what the paired export is meant for
  - Test the handpicked pairing thresholds (60% containment, 5% distance) on real images using the pairing debug PDF

- Low priority: Handle completely blank image stacks
  - Currently handled manually in most cases
  - Prevent nucleus and cytoplasm preprocessing from failing when all slices are blank
