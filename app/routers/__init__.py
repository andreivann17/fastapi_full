"""
Expose the API routers for inclusion in the main application.

Each router module defines API endpoints grouped by resource type.
Importing them here simplifies the ``include_router`` calls in
``app.main``.
"""

from . import auth  # noqa: F401
from . import users  # noqa: F401
from . import patients  # noqa: F401
from . import records  # noqa: F401
from . import detections  # noqa: F401
from . import diagnostic  # noqa: F401
from . import models  # noqa: F401

__all__ = [
    "auth",
    "users",
    "patients",
    "records",
    "detections",
    "diagnostic",
    "models",
]
