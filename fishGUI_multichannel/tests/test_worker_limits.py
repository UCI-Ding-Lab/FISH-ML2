from unittest.mock import MagicMock

import pytest

from fishGUI_multichannel.services.worker_limits import box_generation_worker_limit, segmentation_worker_limit


@pytest.mark.parametrize("total_jobs", [1, 5])
def test_box_generation_uses_one_worker(total_jobs):
    """Find nucleus boxes one frame at a time"""
    assert box_generation_worker_limit(total_jobs) == 1


@pytest.mark.parametrize("device, expected", [("cuda", 2), ("cpu", 4)])
def test_segmentation_worker_limit_uses_the_limit_for_the_backend_device(device, expected):
    """Pick the GPU or CPU limit from the backend's device"""
    backend = MagicMock(device=device)
    assert segmentation_worker_limit(backend, 10, gpu_workers=2, cpu_workers=4) == expected


def test_segmentation_worker_limit_never_exceeds_the_number_of_frames():
    """Do not start more workers than there are frames"""
    assert segmentation_worker_limit(MagicMock(device="cpu"), 2, gpu_workers=2, cpu_workers=5) == 2


def test_segmentation_worker_limit_uses_the_cpu_limit_without_a_backend():
    """Fall back to the CPU limit when the backend is unknown"""
    assert segmentation_worker_limit(None, 10, gpu_workers=2, cpu_workers=3) == 3


def test_segmentation_worker_limit_is_at_least_one():
    """Always allow at least one worker"""
    assert segmentation_worker_limit(MagicMock(device="cpu"), 0, gpu_workers=2, cpu_workers=1) == 1
