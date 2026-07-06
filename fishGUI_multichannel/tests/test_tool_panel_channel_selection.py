from unittest.mock import MagicMock

from fishGUI_multichannel.gui.tools_pannel import seasoning


def _make_bare_tool_panel():
    panel = seasoning.__new__(seasoning)
    panel.gui = MagicMock()
    panel.channel_var = MagicMock()
    panel.channel_selector = MagicMock()
    menu = MagicMock()
    panel.channel_selector.__getitem__.return_value = menu
    return panel


def test_on_channel_change_updates_loaded_image_channel_and_recooks_the_stove():
    panel = _make_bare_tool_panel()
    abs_obj = MagicMock()
    abs_obj._get_seg_obj_for_channel.return_value = ["mask-488"]
    panel.gui.getStove.return_value.getLoaded.return_value = abs_obj

    panel.on_channel_change("488")

    panel.channel_var.set.assert_called_once_with("488")
    abs_obj._get_seg_obj_for_channel.assert_called_once_with("488")
    assert abs_obj.drawSegmentation is True
    assert abs_obj.selected_channel == "488"
    assert abs_obj.seg == ["mask-488"]
    panel.gui.getStove.return_value.cook.assert_called_once_with(abs_obj)


def test_on_channel_change_returns_early_when_no_image_is_loaded():
    panel = _make_bare_tool_panel()
    panel.gui.getStove.return_value.getLoaded.return_value = None

    panel.on_channel_change("DAPI")

    panel.channel_var.set.assert_called_once_with("DAPI")
    panel.gui.getStove.return_value.cook.assert_not_called()


def test_update_channel_selector_for_image_syncs_the_current_channel():
    panel = _make_bare_tool_panel()
    abs_obj = MagicMock(selected_channel="555", available_channels=["555"])

    panel.update_channel_selector_for_image(abs_obj)

    panel.channel_var.set.assert_any_call("555")
    assert panel.channel_var.set.call_args_list[-1] == (("555",), {})


def test_update_channel_menu_rebuilds_options_and_keeps_valid_selection():
    panel = _make_bare_tool_panel()
    menu = panel.channel_selector.__getitem__.return_value
    panel.channel_var.get.return_value = "488"

    panel.update_channel_menu(["647", "488"])

    menu.delete.assert_called_once_with(0, "end")
    assert menu.add_command.call_count == 3
    panel.channel_var.set.assert_called_once_with("488")
    panel.channel_selector.configure.assert_called_once_with(state="normal")


def test_update_channel_menu_defaults_to_dapi_and_disables_selector_for_single_option():
    panel = _make_bare_tool_panel()
    menu = panel.channel_selector.__getitem__.return_value
    panel.channel_var.get.return_value = "594"

    panel.update_channel_menu([])

    menu.delete.assert_called_once_with(0, "end")
    menu.add_command.assert_called_once()
    panel.channel_var.set.assert_called_once_with("DAPI")
    panel.channel_selector.configure.assert_called_once_with(state="disabled")