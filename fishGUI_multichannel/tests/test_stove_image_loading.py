from unittest.mock import MagicMock

from fishGUI_multichannel.gui.canvas.stove import stove


class PatchList(list):
    def __init__(self, items):
        super().__init__(items)
        self.clear_called = False

    def clear(self):
        self.clear_called = True
        super().clear()


def _make_bare_stove():
    stove_obj = stove.__new__(stove)
    stove_obj.ax_img = None
    stove_obj.subplot = MagicMock()
    stove_obj.subplot.patches = []
    stove_obj.canvas = MagicMock()
    stove_obj._refresh_nucleus_centers = MagicMock()
    stove_obj.clearLoaded()
    return stove_obj


def _make_loaded_abstract():
    abs_obj = MagicMock()
    abs_obj.getImgNumpyRGB.return_value = "rgb-image"
    return abs_obj


def test_cook_renders_a_new_image_when_a_frame_is_not_already_loaded():
    stove_obj = _make_bare_stove()
    abs_obj = _make_loaded_abstract()
    ax_img = MagicMock()
    stove_obj.subplot.imshow.return_value = ax_img

    stove_obj.cook(abs_obj)

    assert stove_obj.getLoaded() is abs_obj
    stove_obj.subplot.imshow.assert_called_once_with("rgb-image")
    stove_obj.subplot.set_axis_off.assert_called_once_with()
    stove_obj._refresh_nucleus_centers.assert_called_once_with(abs_obj)
    stove_obj.canvas.draw.assert_called_once_with()
    assert stove_obj.ax_img is ax_img


def test_cook_updates_the_existing_image_when_the_same_frame_is_already_loaded():
    stove_obj = _make_bare_stove()
    abs_obj = _make_loaded_abstract()
    stove_obj.setLoaded(abs_obj)
    stove_obj.ax_img = MagicMock()

    stove_obj.cook(abs_obj)

    stove_obj.ax_img.set_data.assert_called_once_with("rgb-image")
    stove_obj.subplot.imshow.assert_not_called()
    stove_obj.subplot.set_axis_off.assert_called_once_with()
    stove_obj._refresh_nucleus_centers.assert_called_once_with(abs_obj)
    stove_obj.canvas.draw_idle.assert_called_once_with()


def test_dump_clears_the_loaded_frame_removes_patches_and_redraws_the_canvas():
    stove_obj = _make_bare_stove()
    stove_obj.setLoaded(_make_loaded_abstract())
    patch_one = MagicMock()
    patch_two = MagicMock()
    patches = PatchList([patch_one, patch_two])
    stove_obj.subplot.patches = patches

    stove_obj.dump()

    assert stove_obj.getLoaded() is None
    patch_one.remove.assert_called_once_with()
    patch_two.remove.assert_called_once_with()
    assert patches.clear_called is True
    assert patches == []
    stove_obj.subplot.clear.assert_called_once_with()
    stove_obj.subplot.set_axis_off.assert_called_once_with()
    stove_obj.canvas.draw.assert_called_once_with()