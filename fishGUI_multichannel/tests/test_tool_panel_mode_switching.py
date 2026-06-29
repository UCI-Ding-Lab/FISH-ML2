from unittest.mock import MagicMock

from fishGUI_multichannel.gui.tools_pannel import seasoning


def _make_bare_tool_panel(seg_on=False, bbox_on=False):
    panel = seasoning.__new__(seasoning)
    panel.gui = MagicMock()

    func_button = panel.gui.getFuncButton.return_value
    func_button.segButtonPressed.return_value = seg_on
    func_button.bboxButtonPressed.return_value = bbox_on

    brush_var = MagicMock()
    brush_var.get.return_value = 0
    eraser_var = MagicMock()
    eraser_var.get.return_value = 0
    add_bbox_var = MagicMock()
    add_bbox_var.get.return_value = 0
    panel.tools_var = {
        "brush": brush_var,
        "eraser": eraser_var,
        "add_bbox": add_bbox_var,
    }
    return panel


def test_press_act_disables_brush_and_eraser_outside_segmentation_mode():
    panel = _make_bare_tool_panel(seg_on=False, bbox_on=False)

    result = panel.press_act("brush")

    assert result is False
    panel.gui.popBox.assert_called_once_with(
        "w",
        "Tool Disabled",
        "Brush and Eraser are only available when Segmentation mode is ON and BBOX mode is OFF.",
    )
    panel.tools_var["brush"].set.assert_called_once_with(0)
    panel.tools_var["eraser"].set.assert_called_once_with(0)
    panel.tools_var["add_bbox"].set.assert_called_once_with(0)


def test_press_act_keeps_only_one_segmentation_tool_active_at_a_time():
    panel = _make_bare_tool_panel(seg_on=True, bbox_on=False)
    panel.tools_var["brush"].get.return_value = 1
    panel._deactivate_navigation_tool = MagicMock()

    result = panel.press_act("brush")

    assert result is True
    panel.tools_var["eraser"].set.assert_called_once_with(0)
    panel.tools_var["add_bbox"].set.assert_called_once_with(0)
    panel._deactivate_navigation_tool.assert_called_once_with()


def test_deactivate_navigation_tool_uses_toolbar_clear_active_tool_when_available():
    panel = _make_bare_tool_panel()
    toolbar = MagicMock()
    panel.gui.getStove.return_value.toolbar = toolbar

    panel._deactivate_navigation_tool()

    toolbar.clear_active_tool.assert_called_once_with()
    toolbar.deactivate_all_tools.assert_not_called()


def test_deactivate_navigation_tool_falls_back_to_deactivate_all_tools_when_needed():
    panel = _make_bare_tool_panel()
    toolbar = MagicMock()
    toolbar.clear_active_tool.side_effect = RuntimeError("clear failed")
    panel.gui.getStove.return_value.toolbar = toolbar

    panel._deactivate_navigation_tool()

    toolbar.clear_active_tool.assert_called_once_with()
    toolbar.deactivate_all_tools.assert_called_once_with()