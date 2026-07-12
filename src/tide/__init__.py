"""Tide: quality protocol for autonomous coding agents."""

__version__ = "1.0.0"

from . import core as _core
from .agility import install as _install_agility
from .closure import install as _install_closure
from .guardrails import install as _install_guardrails
from .segmentation import install as _install_segmentation
from .v1 import install as _install_v1
from .v1_fixes import install as _install_v1_fixes

_install_guardrails(_core)
_install_agility(_core)
_install_closure(_core)
_install_segmentation(_core)
_install_v1(_core)
_install_v1_fixes(_core)

del _core, _install_guardrails, _install_agility, _install_closure, _install_segmentation, _install_v1, _install_v1_fixes
