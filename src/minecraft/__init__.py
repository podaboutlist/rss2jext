"""Create resource packs for Minecraft and discs.json for Jukebox Extended Reborn."""

from .jext import populate_discs_json  # noqa:F401
from .resource_pack import ResourcePack  # noqa: F401

# This package is versioned independently from the parent project.
__version__ = "1.0.0"
