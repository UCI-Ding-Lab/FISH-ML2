import logging

logger = logging.getLogger('fishcore')

# GroundingDINO box finding after import (used by both nucleus backends)
BOX_GENERATION_WORKERS = 1


def box_generation_worker_limit(total_jobs: int) -> int:
    """Return how many frames may find nucleus boxes at the same time."""
    worker_count = max(1, min(BOX_GENERATION_WORKERS, total_jobs))
    logger.info("Nucleus box generation is using %s worker(s).", worker_count)
    return worker_count


def segmentation_worker_limit(backend, total_jobs: int, gpu_workers: int, cpu_workers: int) -> int:
    """Return how many frames may run segmentation at the same time on the backend's device."""
    on_gpu = getattr(backend, "device", None) == "cuda"
    limit = gpu_workers if on_gpu else cpu_workers
    worker_count = max(1, min(limit, total_jobs))
    logger.info("Segmentation is using %s worker(s) on %s.", worker_count, "GPU" if on_gpu else "CPU")
    return worker_count
