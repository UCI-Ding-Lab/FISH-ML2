from unittest.mock import MagicMock, patch

import pytest

from fishGUI_multichannel.services import worker_limits
from fishGUI_multichannel.services.worker_limits import box_generation_worker_limit, segmentation_worker_limit


@pytest.mark.parametrize("total_jobs", [1, 5])
def test_box_generation_uses_one_worker(total_jobs):
    """Find nucleus boxes one frame at a time"""
    assert box_generation_worker_limit(total_jobs) == 1


@pytest.mark.parametrize("device", ["cuda", "cpu"])
def test_segmentation_runs_one_frame_at_a_time_until_parallel_runs_are_verified(device):
    """Keep segmentation sequential on both devices until 1 vs 3 workers is compared"""
    assert segmentation_worker_limit(MagicMock(device=device), 10) == 1


@pytest.fixture
def three_gpu_workers():
    """Use three GPU workers so the device logic can be checked independently of the current setting."""
    with patch.object(worker_limits, "SEGMENTATION_WORKERS_ON_GPU", 3), \
         patch.object(worker_limits, "SEGMENTATION_WORKERS_ON_CPU", 1):
        yield


@pytest.mark.parametrize("device, expected", [("cuda", 3), ("cpu", 1)])
def test_segmentation_uses_the_limit_for_the_backend_device(three_gpu_workers, device, expected):
    """Pick the GPU or CPU limit from the backend's device"""
    assert segmentation_worker_limit(MagicMock(device=device), 10) == expected


def test_segmentation_worker_limit_never_exceeds_the_number_of_frames(three_gpu_workers):
    """Do not start more workers than there are frames"""
    assert segmentation_worker_limit(MagicMock(device="cuda"), 2) == 2


def test_segmentation_worker_limit_uses_the_cpu_limit_without_a_backend(three_gpu_workers):
    """Fall back to the CPU limit when the backend is unknown"""
    assert segmentation_worker_limit(None, 10) == 1


def test_segmentation_worker_limit_is_at_least_one(three_gpu_workers):
    """Always allow at least one worker"""
    assert segmentation_worker_limit(MagicMock(device="cuda"), 0) == 1
