import numpy as np
import pytest

from fishGUI_multichannel.services.composite import build_composite, default_channel_colors

RED, GREEN, BLUE = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)
YELLOW, MAGENTA, WHITE = (1.0, 1.0, 0.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0)


def _one_bright_pixel(y=0, x=0):
    img = np.zeros((16, 16), dtype=np.uint8)
    img[y, x] = 255
    return img


def test_composite_is_a_uint8_rgb_image_the_size_of_the_channels():
    composite = build_composite({"DAPI": _one_bright_pixel(), "647": _one_bright_pixel()}, {"DAPI": BLUE, "647": RED})
    assert composite.shape == (16, 16, 3)
    assert composite.dtype == np.uint8


def test_each_channel_is_tinted_in_its_color():
    images = {"DAPI": _one_bright_pixel(0, 0), "488": _one_bright_pixel(4, 4), "647": _one_bright_pixel(8, 8)}
    composite = build_composite(images, {"DAPI": BLUE, "488": GREEN, "647": RED})
    assert tuple(composite[0, 0]) == (0, 0, 255)
    assert tuple(composite[4, 4]) == (0, 255, 0)
    assert tuple(composite[8, 8]) == (255, 0, 0)
    assert tuple(composite[12, 12]) == (0, 0, 0)


def test_colocalized_channels_mix_their_colors():
    composite = build_composite({"488": _one_bright_pixel(), "647": _one_bright_pixel()}, {"488": GREEN, "647": RED})
    assert tuple(composite[0, 0]) == (255, 255, 0)


def test_composite_needs_at_least_one_channel():
    with pytest.raises(ValueError):
        build_composite({}, {})


def test_dapi_is_blue_and_647_is_red():
    colors = default_channel_colors(["DAPI", "488", "647"])
    assert colors == {"DAPI": BLUE, "647": RED, "488": GREEN}


def test_647_is_red_even_when_it_is_not_the_shortest_wavelength():
    colors = default_channel_colors(["DAPI", "647", "555", "488"])
    assert colors == {"DAPI": BLUE, "647": RED, "488": GREEN, "555": YELLOW}


def test_without_647_the_shortest_wavelength_is_red_then_green_then_yellow():
    colors = default_channel_colors(["DAPI", "594", "488", "555"])
    assert colors == {"DAPI": BLUE, "488": RED, "555": GREEN, "594": YELLOW}


def test_a_single_cytoplasm_channel_is_red():
    assert default_channel_colors(["DAPI", "555"])["555"] == RED


def test_channels_without_a_wavelength_come_last_and_turn_white_after_magenta():
    colors = default_channel_colors(["DAPI", "CY5", "488", "514", "555", "594"])
    assert colors["CY5"] == WHITE
    assert colors["594"] == MAGENTA
