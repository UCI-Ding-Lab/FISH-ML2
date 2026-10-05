import tkinter as tk

from ..services.export_modes import EXPORT_MODE_LABELS


def ask_export_mode(root, initial_mode: str, available_modes: list[str] | None = None) -> str | None:
    """
    Show the export mode popup and return the chosen mode, or None when the user cancels.
    Modes missing from available_modes are shown greyed out.
    """
    if available_modes is None:
        available_modes = list(EXPORT_MODE_LABELS)
    popup = tk.Toplevel(root)
    popup.title("Choose Export Mode")
    popup.resizable(False, False)

    choice = tk.StringVar(master=popup, value=initial_mode)
    chosen = {"mode": None}

    tk.Label(popup, text="Which masks should be exported?").pack(padx=20, pady=8)
    for mode, label in EXPORT_MODE_LABELS.items():
        state = tk.NORMAL if mode in available_modes else tk.DISABLED
        tk.Radiobutton(popup, text=label, variable=choice, value=mode, state=state).pack(anchor="w", padx=20)
    if len(available_modes) < len(EXPORT_MODE_LABELS):
        note = "Whole-cell modes need cytoplasm images.\nOnly DAPI images are loaded."
        tk.Label(popup, text=note, fg="gray").pack(padx=20, pady=(4, 0))

    def confirm():
        """Keep the selected mode and close the popup."""
        chosen["mode"] = choice.get()
        popup.destroy()

    button_row = tk.Frame(popup)
    button_row.pack(pady=10)
    tk.Button(button_row, text="Export", command=confirm).pack(side=tk.LEFT, padx=5)
    tk.Button(button_row, text="Cancel", command=popup.destroy).pack(side=tk.LEFT, padx=5)

    popup.transient(root)
    popup.grab_set()
    root.wait_window(popup)
    return chosen["mode"]
