"""Tide: minimal quality protocol for AI coding agents."""

__version__ = "0.6.0a7"

from . import core as _core
from .agility import install as _install_agility
from .closure import install as _install_closure
from .guardrails import install as _install_guardrails
from .segmentation import install as _install_segmentation

_install_guardrails(_core)
_install_agility(_core)
_install_closure(_core)
_install_segmentation(_core)

del _core, _install_guardrails, _install_agility, _install_closure, _install_segmentation
