"""
Build the colored composite image shown in the View Composite window.
"""
import numpy as np

Color = tuple[float, float, float]

DAPI_COLOR = (0.0, 0.0, 1.0)  # blue
# Cytoplasm colors in order: 647 (or the first channel) red, then green, yellow, magenta
CYTOPLASM_COLORS = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 1.0, 0.0), (1.0, 0.0, 1.0)]
FALLBACK_COLOR = (1.0, 1.0, 1.0)  # white once the colors above run out


def _wavelength(channel: str) -> float:
    """Return the channel's wavelength for sorting, putting names that are not a wavelength last."""
    return float(channel) if channel.isdigit() else float("inf")


def default_channel_colors(channels: list[str]) -> dict[str, Color]:
    """
    Pick each channel's starting color: DAPI blue, 647 red, and the other cytoplasm
    channels green, yellow, magenta by wavelength. Without 647 the first one is red.
    """
    cytoplasm = sorted((ch for ch in channels if ch != "DAPI"), key=_wavelength)
    if "647" in cytoplasm:
        cytoplasm.remove("647")
        cytoplasm.insert(0, "647")
    colors = {"DAPI": DAPI_COLOR} if "DAPI" in channels else {}
    for i, ch in enumerate(cytoplasm):
        colors[ch] = CYTOPLASM_COLORS[i] if i < len(CYTOPLASM_COLORS) else FALLBACK_COLOR
    return colors


def build_composite(channel_images: dict[str, np.ndarray], colors: dict[str, Color]) -> np.ndarray:
    """
    Tint each uint8 grayscale channel in its color and add them into one uint8 RGB image.
    """
    if not channel_images:
        raise ValueError("build_composite needs at least one channel image.")
    shape = next(iter(channel_images.values())).shape
    composite = np.zeros((*shape, 3), dtype=np.float32)
    for channel, img in channel_images.items():
        color = np.array(colors[channel], dtype=np.float32)
        composite += (img.astype(np.float32) / 255)[..., None] * color
    return (np.clip(composite, 0, 1) * 255).astype(np.uint8)
