import tkinter as tk

import pytest

from fishGUI_multichannel.gui.export_mode_popup import ask_export_mode
from fishGUI_multichannel.services.export_modes import BOTH, NUCLEUS_ONLY, WHOLE_CELL_ONLY


@pytest.fixture(scope="module")
def root():
    """Create one hidden Tk root for these tests, or skip when no display is available."""
    try:
        tk_root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"Tk display is not available: {error}")
    tk_root.withdraw()
    yield tk_root
    tk_root.destroy()


def find_widgets(widget, widget_type):
    """Return every child widget of one type, searching nested frames."""
    found = []
    for child in widget.winfo_children():
        if isinstance(child, widget_type):
            found.append(child)
        found.extend(find_widgets(child, widget_type))
    return found


def run_popup(root, initial_mode, action):
    """Open the popup and run one action on it once it is shown."""
    def act():
        popup = find_widgets(root, tk.Toplevel)[-1]
        action(popup)

    root.after(50, act)
    return ask_export_mode(root, initial_mode)


def click_button(popup, text):
    """Click the popup button with the given text."""
    button = next(b for b in find_widgets(popup, tk.Button) if b.cget("text") == text)
    button.invoke()


def test_export_returns_the_initial_mode(root):
    assert run_popup(root, WHOLE_CELL_ONLY, lambda popup: click_button(popup, "Export")) == WHOLE_CELL_ONLY


def test_export_returns_the_mode_the_user_selects(root):
    def choose_nucleus_then_export(popup):
        radio = next(r for r in find_widgets(popup, tk.Radiobutton) if r.cget("value") == NUCLEUS_ONLY)
        radio.invoke()
        click_button(popup, "Export")

    assert run_popup(root, BOTH, choose_nucleus_then_export) == NUCLEUS_ONLY


def test_cancel_returns_none(root):
    assert run_popup(root, BOTH, lambda popup: click_button(popup, "Cancel")) is None


def test_closing_the_window_returns_none(root):
    assert run_popup(root, BOTH, lambda popup: popup.destroy()) is None


def test_popup_lists_all_three_modes(root):
    values = []

    def read_modes_then_cancel(popup):
        values.extend(r.cget("value") for r in find_widgets(popup, tk.Radiobutton))
        click_button(popup, "Cancel")

    run_popup(root, BOTH, read_modes_then_cancel)
    assert values == [NUCLEUS_ONLY, WHOLE_CELL_ONLY, BOTH]
