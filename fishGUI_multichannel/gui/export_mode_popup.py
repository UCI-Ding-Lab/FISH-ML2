import tkinter as tk

from ..services.export_modes import EXPORT_MODE_LABELS


def ask_export_mode(root, initial_mode: str) -> str | None:
    """
    Show the export mode popup and return the chosen mode, or None when the user cancels.
    """
    popup = tk.Toplevel(root)
    popup.title("Choose Export Mode")
    popup.resizable(False, False)

    choice = tk.StringVar(master=popup, value=initial_mode)
    chosen = {"mode": None}

    tk.Label(popup, text="Which masks should be exported?").pack(padx=20, pady=8)
    for mode, label in EXPORT_MODE_LABELS.items():
        tk.Radiobutton(popup, text=label, variable=choice, value=mode).pack(anchor="w", padx=20)

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
