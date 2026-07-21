from unittest.mock import MagicMock, patch

from fishGUI_multichannel.gui.abstract import abstract
from fishGUI_multichannel.services.session_manager import SessionManager


def _make_pool_abstract(selected=False):
    abs_obj = abstract.__new__(abstract)
    abs_obj._abstract__selected = selected
    abs_obj._abstract__selected_for_segmentation = False
    abs_obj._abstract__thumbnail_state = None
    abs_obj._abstract__img_tk_thumbnail = object()
    abs_obj._abstract__img_tk_thumbnail_bbox = object()
    abs_obj._abstract__img_tk_thumbnail_select = object()
    abs_obj._abstract__img_tk_thumbnail_crossout = object()
    abs_obj._abstract__img_tk_thumbnail_segmented = object()
    abs_obj._abstract__img_tk_thumbnail_segmentation_selected = object()
    abs_obj._abstract__img_tk_thumbnail_selected_and_segmented = object()
    abs_obj._abstract__img_pil_thumbnail = MagicMock()
    abs_obj._abstract__img_pil_thumbnail_bbox = MagicMock()
    abs_obj._abstract__label = MagicMock()
    abs_obj.getLabel = MagicMock(return_value=abs_obj._abstract__label)
    abs_obj.update_thumbnail = MagicMock()
    abs_obj.gui = MagicMock()
    abs_obj.gui.getFuncButton.return_value.selectButtonPressed.return_value = False
    abs_obj.available_channels = ["647", "488"]
    abs_obj._abstract__bbox = [MagicMock(final=[1, 2, 3, 4])]
    abs_obj._abstract__bbox_generated = True
    abs_obj.get_segments = MagicMock(return_value=[])
    abs_obj.get_nucleus_segments = MagicMock(return_value=[])
    abs_obj.getNucleusPath = MagicMock(return_value="nucleus.tif")
    abs_obj.getCytoplasmPaths = MagicMock(return_value=["cyto_647.tif", "cyto_488.tif"])
    abs_obj.selected_channel = "647"
    abs_obj.sample_id = "sample-001"
    abs_obj.on_click = MagicMock()
    return abs_obj


def test_select_all_marks_every_object_in_the_pool_as_selected():
    first = _make_pool_abstract(selected=False)
    second = _make_pool_abstract(selected=False)
    SessionManager._SessionManager__pool = [first, second]

    SessionManager.selectAll()

    assert first.selected is True
    assert second.selected is True


def test_remove_unselected_keeps_selected_frames_and_refocuses_after_cleanup():
    selected_frame = _make_pool_abstract(selected=True)
    removed_frame = _make_pool_abstract(selected=False)
    SessionManager._SessionManager__pool = [selected_frame, removed_frame]

    with patch.object(SessionManager, "sendFirst") as mock_send_first:
        SessionManager.removeUnselected()

    assert SessionManager.getPool() == [selected_frame]
    assert selected_frame.thumbnail == "default"
    mock_send_first.assert_called_once_with()


def test_remove_segmentation_selection_clears_segmentation_flags_for_all_frames():
    first = _make_pool_abstract()
    second = _make_pool_abstract()
    first.selected_for_segmentation = True
    second.selected_for_segmentation = True
    SessionManager._SessionManager__pool = [first, second]

    SessionManager.remove_segmentation_selection()

    assert first.selected_for_segmentation is False
    assert second.selected_for_segmentation is False


def test_get_all_available_channels_returns_unique_sorted_channels():
    first = _make_pool_abstract()
    second = _make_pool_abstract()
    first.available_channels = ["647", "488"]
    second.available_channels = ["555", "488"]
    SessionManager._SessionManager__pool = [first, second]

    assert SessionManager.get_all_available_channels() == ["488", "555", "647"]


def test_grab_pool_bundles_only_selected_frames():
    selected_frame = _make_pool_abstract(selected=True)
    selected_frame.sample_id = "sample-007"
    selected_frame.get_segments = MagicMock(side_effect=lambda ch: [MagicMock(_segment__data=MagicMock(T=f"mask-{ch}"))])
    selected_frame.get_nucleus_segments = MagicMock(return_value=[MagicMock(_segment__data=MagicMock(T="mask-DAPI"))])
    unselected_frame = _make_pool_abstract(selected=False)
    SessionManager._SessionManager__pool = [selected_frame, unselected_frame]

    with patch("fishGUI_multichannel.services.session_manager.bundle") as mock_bundle:
        result = SessionManager.grabPool()

    mock_bundle.assert_called_once_with(
        "sample-007",
        nucleus_path="nucleus.tif",
        cyto_paths=["cyto_647.tif", "cyto_488.tif"],
        bbox=[[1, 2, 3, 4]],
        segment={"647": ["mask-647"], "488": ["mask-488"]},
        nucleus_segment=["mask-DAPI"],
        selected_channel="647",
    )
    assert result == [mock_bundle.return_value]
