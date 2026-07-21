from unittest.mock import MagicMock, patch

from fishGUI_multichannel.gui.toolbar import FishToolBar


def _make_bare_toolbar():
    toolbar = FishToolBar.__new__(FishToolBar)
    toolbar.fishGUI = MagicMock()
    toolbar.fishGUI.getSeasoning.return_value.tools_var = {
        "brush": MagicMock(),
        "eraser": MagicMock(),
        "add_mask": MagicMock(),
    }
    toolbar.set_message = MagicMock()
    toolbar._update_buttons_checked = MagicMock()
    toolbar.mode = ""
    toolbar._active = ""
    return toolbar


def test_reset_tool_bank_turns_off_brush_eraser_and_add_mask():
    toolbar = _make_bare_toolbar()

    toolbar.resetToolBank()

    toolbar.fishGUI.getSeasoning.return_value.tools_var["brush"].set.assert_called_once_with(0)
    toolbar.fishGUI.getSeasoning.return_value.tools_var["eraser"].set.assert_called_once_with(0)
    toolbar.fishGUI.getSeasoning.return_value.tools_var["add_mask"].set.assert_called_once_with(0)


def test_zoom_resets_tool_bank_before_delegating_to_the_base_toolbar():
    toolbar = _make_bare_toolbar()

    with patch.object(FishToolBar, "resetToolBank") as mock_reset, \
         patch("fishGUI_multichannel.gui.toolbar.NavigationToolbar2Tk.zoom") as mock_super_zoom:
        FishToolBar.zoom(toolbar)

    mock_reset.assert_called_once_with()
    mock_super_zoom.assert_called_once_with()


def test_is_tool_active_returns_true_when_mode_or_active_flag_is_set():
    toolbar = _make_bare_toolbar()
    toolbar.mode = "zoom rect"
    assert toolbar.is_tool_active() is True

    toolbar.mode = ""
    toolbar._active = "PAN"
    assert toolbar.is_tool_active() is True

    toolbar._active = ""
    assert toolbar.is_tool_active() is False


def test_clear_active_tool_resets_mode_message_and_active_flag():
    toolbar = _make_bare_toolbar()
    toolbar.mode = "zoom rect"
    toolbar._active = "PAN"

    toolbar.clear_active_tool()

    assert toolbar.mode == ""
    assert toolbar._active == ""
    toolbar.set_message.assert_called_once_with("")
    toolbar._update_buttons_checked.assert_called_once_with()


def test_clear_active_tool_ignores_button_refresh_failures():
    toolbar = _make_bare_toolbar()
    toolbar.mode = "zoom rect"
    toolbar._update_buttons_checked.side_effect = RuntimeError("refresh failed")

    toolbar.clear_active_tool()

    assert toolbar.mode == ""
    toolbar.set_message.assert_called_once_with("")
