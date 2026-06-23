import numpy as np
from matplotlib.patches import PathPatch
from matplotlib.path import Path

from fishGUI_multichannel.services import pairing


def make_fake_segment():
    """Build a tiny segment-like object for debug PDF tests."""
    class FakeSegment:
        """Store one reusable outline patch and one small binary mask."""

        def __init__(self):
            self._segment__data = np.ones((2, 2), dtype=np.uint8)
            vertices = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])
            codes = np.array([Path.MOVETO, Path.LINETO, Path.LINETO])
            self._patch = PathPatch(Path(vertices, codes))

        @property
        def patch(self):
            """Return the cached outline patch used by the test segment."""
            return self._patch

    return FakeSegment()


def test_build_outline_patch_returns_a_fresh_patch():
    """Ensure the PDF export path clones segment outlines before drawing them."""
    seg_obj = make_fake_segment()

    outline = pairing.build_outline_patch(seg_obj, "lime")

    assert outline is not seg_obj.patch
    assert np.array_equal(outline.get_path().vertices, seg_obj.patch.get_path().vertices)


def test_export_pairing_debug_pdf_returns_none_when_page_render_fails(tmp_path, monkeypatch):
    """Ensure MAT export can continue when the optional pairing PDF fails."""
    dummy_page = [(object(), "647", {"pairs": [], "unmatched_nuclei": [], "unmatched_cytoplasms": []})]
    monkeypatch.setattr(pairing, "collect_pairing_debug_pages", lambda frames: dummy_page)
    monkeypatch.setattr(pairing, "create_pairing_figure", lambda frame, channel, pairing_data: (_ for _ in ()).throw(MemoryError("boom")))

    pdf_path = pairing.export_pairing_debug_pdf([object()], tmp_path)

    assert pdf_path is None
    assert not (tmp_path / f"{tmp_path.name}_pairing_debug.pdf").exists()
