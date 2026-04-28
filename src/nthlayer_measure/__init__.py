"""nthlayer-measure (DEPRECATED) — superseded by nthlayer-workers (measure module).

This package is deprecated as of v1.0.0 (2026-04-28). Functionality moved to
nthlayer-workers as part of the v1.5 tiered architecture consolidation.

Replacement: pip install nthlayer-workers

The measure functionality is now implemented as the MeasureModule worker
inside nthlayer-workers — same evaluation pipeline (model-driven quality
scoring, calibration, governance, tiered evaluation, OpenSRM SLO polling),
now running as a worker module within the consolidated runtime that talks
to nthlayer-core via HTTP API.

Migration: https://github.com/rsionnach/nthlayer-measure
"""

import warnings as _warnings

_warnings.warn(
    "nthlayer-measure is deprecated. Functionality moved to nthlayer-workers "
    "as of v1.5 (MeasureModule). "
    "Install: pip install nthlayer-workers. "
    "Migration: https://github.com/rsionnach/nthlayer-measure",
    DeprecationWarning,
    stacklevel=2,
)
del _warnings

__version__ = "1.0.0"
