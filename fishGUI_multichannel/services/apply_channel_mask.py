from ..gui.canvas.segment import segment
from tkinter import messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import os
import logging
import time

logger = logging.getLogger("fishcore")

# --- Helper Functions --- 
def ensure_channel_segmented(frame, channel):
    """
    Ensures the segmentation for the given channel is computed for this frame.
    If not already segmented, triggers segmentation for the selected channel.
    """
    if not frame._get_seg_list_for_channel(channel):
        current_focused_channel = frame.selected_channel
        frame.selected_channel = channel
        logger.debug(f"  segmenting channel {channel} for frame {frame.sample_id}")
        _ = frame.segment  # calls segment property in abstract.py -- triggers segmentation for selected channel
        frame.selected_channel = current_focused_channel 
        logger.debug(f"  segmentation done for channel {channel} for frame {frame.sample_id}")


def extract_finalized_masks(frame, source_channel):
    """
    Extracts finalized mask arrays from the source channel for a frame.
    """
    seg_objs = frame._get_seg_list_for_channel(source_channel) or []
    mask_list = [obj._segment__data.T for obj in seg_objs] # TODO check why it needs to be transposed -- consistency with export, matlab program?
    frame.set_finalized_mask(mask_list)
    logger.debug(f"Built {len(mask_list)} masks for frame {frame.sample_id}")
    return mask_list


def apply_masks_on_main(frame, target_channels, mask_list):
    """
    On main thread: applies mask list to all target channels and updates state.
    """
    try:
        shared_segs = [segment(frame.gui, m) for m in mask_list] if mask_list else []
        for ch in target_channels:
            logger.debug(f"Applying mask to channel {ch} for frame {frame.sample_id}")
            for old_seg in frame._get_seg_list_for_channel(ch):
                try:
                    old_seg.draw = False
                except Exception:
                    pass
            frame._set_seg_list_for_channel(ch, shared_segs)
        frame.seg = frame._get_seg_list_for_channel(frame.selected_channel)
        frame.segment_generated = True
    except Exception as e:
        logger.error(f"Failed to apply masks: {e}", exc_info=True)


def update_ui_for_focused_frame(frame, focused_frame, seg_mode_on):
    """
    Updates UI overlay for the focused frame if needed.
    """
    try:
        if frame is focused_frame and seg_mode_on:
            frame.drawSegmentation = True
    except Exception as e:
        logger.error(f"UI update failed: {e}", exc_info=True)


def _resolve_frame_indices(frame_pool, selected_frames):
    if selected_frames == "all":
        return list(range(len(frame_pool)))
    if isinstance(selected_frames, range):
        return list(selected_frames)
    if isinstance(selected_frames, (list, tuple)) and selected_frames:
        if isinstance(selected_frames[0], int):
            return list(selected_frames)
    return [i for i, f in enumerate(frame_pool) if f in selected_frames]


def apply_channel_mask_to_frames(
    abstract_cls, source_channel, selected_frames, target_channels, on_done=None
):
    """
    Applies the mask from source_channel to all target_channels for selected frames.
    Runs compute in background threads, UI updates on main thread.
    """
    frame_pool = abstract_cls.getPool()
    frame_indices = _resolve_frame_indices(frame_pool, selected_frames)
    focused_frame = abstract_cls.getBuffer()
    try:
        seg_mode_on = bool(focused_frame and focused_frame.gui.getFuncButton().segButtonPressed())
    except Exception:
        seg_mode_on = False
    root = _get_gui_root(abstract_cls, frame_pool)

    def _get_inference_worker_limit(total_jobs):
        try:
            backend = None
            if focused_frame is not None and focused_frame.gui is not None:
                backend = focused_frame.gui.getBackEnd()
            elif frame_pool and frame_pool[0].gui is not None:
                backend = frame_pool[0].gui.getBackEnd()
            if getattr(backend, "device", "cpu") == "cuda":
                logger.info("GPU detected; limiting apply-channel concurrency to 1 worker.")
                return 1
        except Exception:
            pass
        return max(1, min(5, os.cpu_count() or 1, total_jobs))

    def compute_worker(i):
        frame = frame_pool[i]
        sid = frame.sample_id
        if not frame.bbox_generated:
            logger.info(f"Skipping frame {sid}: no bbox")
            return ("skipped", sid, frame, None, None)
        try:
            ensure_channel_segmented(frame, source_channel)
            masks = extract_finalized_masks(frame, source_channel)
            return ("ok", sid, frame, masks, frame.available_channels)
        except Exception as e:
            logger.error(f"Compute failed for {sid}: {e}", exc_info=True)
            return ("error", sid, frame, None, None)

    def apply_results_on_main(results):
        skipped = []
        for status, sid, frame, masks, targets in results:
            if status == "skipped":
                skipped.append(sid)
                continue
            if status == "error":
                continue
            apply_masks_on_main(frame, targets, masks)
            update_ui_for_focused_frame(frame, focused_frame, seg_mode_on)
            logger.debug(f"Applied mask to frame {sid}")
        if skipped:
            try:
                messagebox.showinfo("Skipped Frames", f"No bounding box for: {', '.join(skipped)}")
            except Exception:
                logger.info(f"Skipped Frames: {', '.join(skipped)}")
        if on_done:
            try:
                on_done()
            except Exception:
                logger.warning("on_done callback raised", exc_info=True)

    def coordinator():
        start = time.perf_counter()
        results = []
        max_workers = _get_inference_worker_limit(len(frame_indices))
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ApplyMask") as ex:
            futures = {ex.submit(compute_worker, i): i for i in frame_indices}
            for fut in as_completed(futures):
                results.append(fut.result())
        logger.info(f"Apply Channel Mask: processed {len(results)} frames in {time.perf_counter() - start:.2f}s")
        if root is not None:
            root.after(0, lambda: apply_results_on_main(results))
        else:
            apply_results_on_main(results)

    threading.Thread(target=coordinator, daemon=True, name="ApplyChannelMaskCoordinator").start()

def _get_gui_root(abstract_cls, frame_pool):
    """
    Returns the Tk root widget for scheduling UI updates.
    """
    try:
        if frame_pool and frame_pool[0].gui:
            return frame_pool[0].gui.getRoot()
        if hasattr(abstract_cls, "getRoot"):
            return abstract_cls.getRoot()
    except Exception:
        pass
    return None
