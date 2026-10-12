import tkinter as tk
from unittest.mock import MagicMock, patch

import pytest

from fishGUI_multichannel.gui import stored_masks_popup
from fishGUI_multichannel.gui.stored_masks_popup import (
    CHOOSE_PER_FRAME,
    RESEGMENT_ALL,
    USE_STORED,
    ask_stored_masks_choice,
    choose_frames_to_resegment,
)


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


def click_after_open(root, button_text):
    """Click one popup button once the popup is shown."""
    def click():
        popup = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        buttons = [b for row in popup.winfo_children() for b in row.winfo_children() if isinstance(b, tk.Button)]
        next(b for b in buttons if b.cget("text") == button_text).invoke()

    root.after(50, click)


@pytest.mark.parametrize("button_text, expected", [
    ("Use stored for all", USE_STORED),
    ("Re-segment all", RESEGMENT_ALL),
    ("Choose per frame", CHOOSE_PER_FRAME),
    ("Cancel", None),
])
def test_each_button_returns_its_choice(root, button_text, expected):
    click_after_open(root, button_text)
    assert ask_stored_masks_choice(root, "Stored Nucleus Masks", 6, 10, "nucleus masks") == expected


def make_frames(count):
    """Build frame doubles with sample ids s001, s002, ..."""
    return [MagicMock(sample_id=f"s{i:03d}") for i in range(1, count + 1)]


def test_no_question_when_no_frame_has_masks():
    frames = make_frames(3)
    with patch.object(stored_masks_popup, "ask_stored_masks_choice") as ask:
        assert choose_frames_to_resegment(MagicMock(), "Title", frames, [], "nucleus masks") == []
    ask.assert_not_called()


@pytest.mark.parametrize("choice, expected_indexes", [(USE_STORED, []), (RESEGMENT_ALL, [0, 1]), (None, None)])
def test_single_choice_decides_for_every_frame_with_masks(choice, expected_indexes):
    frames = make_frames(3)
    with_masks = frames[:2]
    with patch.object(stored_masks_popup, "ask_stored_masks_choice", return_value=choice):
        result = choose_frames_to_resegment(MagicMock(), "Title", frames, with_masks, "nucleus masks")
    expected = None if expected_indexes is None else [with_masks[i] for i in expected_indexes]
    assert result == expected


def test_choose_per_frame_asks_each_frame_with_masks_once():
    frames = make_frames(3)
    with_masks = frames[:2]
    with patch.object(stored_masks_popup, "ask_stored_masks_choice", return_value=CHOOSE_PER_FRAME), \
         patch.object(stored_masks_popup.messagebox, "askyesno", side_effect=[True, False]) as askyesno:
        result = choose_frames_to_resegment(MagicMock(), "Title", frames, with_masks, "nucleus masks")
    assert result == [with_masks[0]]
    assert askyesno.call_count == 2
    assert "s001 already has nucleus masks. Re-segment it?" in askyesno.call_args_list[0].args
