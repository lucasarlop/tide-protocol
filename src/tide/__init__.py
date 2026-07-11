"""Tide: minimal quality protocol for AI coding agents."""

__version__ = "0.6.0a6"

from . import core as _core
from .guardrails import install as _install_guardrails
from .agility import install as _install_agility

_install_guardrails(_core)
_install_agility(_core)

del _core, _install_guardrails, _install_agility
