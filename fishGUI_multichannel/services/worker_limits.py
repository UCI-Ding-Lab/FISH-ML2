import logging

logger = logging.getLogger('fishcore')

# GroundingDINO box finding after import (used by both nucleus backends)
BOX_GENERATION_WORKERS = 1

# Segmentation model runs (nucleus, cytoplasm, and copy-mask source segmentation)
# GPU: parallel runs share GPU memory; lower this if "CUDA out of memory" errors appear.
# Kept at 1 until 1 vs 3 workers is compared on the same frames: parallel runs share one model,
# and earlier parallel settings were reverted to 1 (Jul 15 and Aug 17, 2026) without a recorded reason.
SEGMENTATION_WORKERS_ON_GPU = 1
# CPU: one run already uses every core, so extra runs mostly compete for the same cores
SEGMENTATION_WORKERS_ON_CPU = 1


def box_generation_worker_limit(total_jobs: int) -> int:
    """Return how many frames may find nucleus boxes at the same time."""
    worker_count = max(1, min(BOX_GENERATION_WORKERS, total_jobs))
    logger.info("Nucleus box generation is using %s worker(s).", worker_count)
    return worker_count


def segmentation_worker_limit(backend, total_jobs: int) -> int:
    """Return how many frames may run segmentation at the same time on the backend's device."""
    on_gpu = getattr(backend, "device", None) == "cuda"
    limit = SEGMENTATION_WORKERS_ON_GPU if on_gpu else SEGMENTATION_WORKERS_ON_CPU
    worker_count = max(1, min(limit, total_jobs))
    logger.info("Segmentation is using %s worker(s) on %s.", worker_count, "GPU" if on_gpu else "CPU")
    return worker_count
