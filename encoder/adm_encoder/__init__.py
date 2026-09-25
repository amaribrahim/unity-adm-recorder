"""Encode a recorded session JSON and mono stems into an ADM BWF master."""

import warnings

# Import-time noise from ear and its pinned attrs; not actionable for users of this tool.
warnings.filterwarnings(
    "ignore",
    message="Running interpreter doesn't sufficiently support code object introspection",
    category=RuntimeWarning,
)
warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API", category=UserWarning)
