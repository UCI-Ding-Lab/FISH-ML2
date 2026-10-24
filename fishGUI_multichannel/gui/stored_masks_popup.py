import tkinter as tk
from tkinter import messagebox

USE_STORED = "use_stored"
RESEGMENT_ALL = "resegment_all"
CHOOSE_PER_FRAME = "choose_per_frame"


def ask_stored_masks_choice(root, title: str, frames_with_masks: int, total_frames: int, mask_kind: str) -> str | None:
    """
    Ask once what to do with frames that already have masks.
    Return USE_STORED, RESEGMENT_ALL, CHOOSE_PER_FRAME, or None when the user cancels.
    """
    popup = tk.Toplevel(root)
    popup.title(title)
    popup.resizable(False, False)
    chosen = {"choice": None}

    message = f"{frames_with_masks} of {total_frames} frames already have {mask_kind}."
    tk.Label(popup, text=message).pack(padx=20, pady=(12, 8))

    def choose(choice):
        """Keep the clicked choice and close the popup."""
        chosen["choice"] = choice
        popup.destroy()

    button_row = tk.Frame(popup)
    button_row.pack(padx=10, pady=(0, 12))
    tk.Button(button_row, text="Use stored for all", command=lambda: choose(USE_STORED)).pack(side=tk.LEFT, padx=4)
    tk.Button(button_row, text="Re-segment all", command=lambda: choose(RESEGMENT_ALL)).pack(side=tk.LEFT, padx=4)
    tk.Button(button_row, text="Choose per frame", command=lambda: choose(CHOOSE_PER_FRAME)).pack(side=tk.LEFT, padx=4)
    tk.Button(button_row, text="Cancel", command=popup.destroy).pack(side=tk.LEFT, padx=4)

    popup.transient(root)
    popup.grab_set()
    root.wait_window(popup)
    return chosen["choice"]


def choose_frames_to_resegment(root, title: str, frames: list, frames_with_masks: list, mask_kind: str) -> list | None:
    """
    Ask on the main thread, before segmentation starts, which frames with stored masks to re-segment.
    Return the frames to re-segment (empty means keep all stored masks), or None when the user cancels.
    """
    if not frames_with_masks:
        return []
    choice = ask_stored_masks_choice(root, title, len(frames_with_masks), len(frames), mask_kind)
    if choice is None:
        return None
    if choice == USE_STORED:
        return []
    if choice == RESEGMENT_ALL:
        return list(frames_with_masks)
    return [
        frame
        for frame in frames_with_masks
        if messagebox.askyesno(title, f"{frame.sample_id} already has {mask_kind}. Re-segment it?", parent=root)
    ]
