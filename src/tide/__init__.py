"""Tide: quality protocol for autonomous coding agents."""

__version__ = "1.1.1"

from . import core as _core
from .agility import install as _install_agility
from .autonomy import install as _install_autonomy
from .closure import install as _install_closure
from .guardrails import install as _install_guardrails
from .maintenance import install as _install_maintenance
from .model_policy import install as _install_model_policy
from .segmentation import install as _install_segmentation
from .v1 import install as _install_v1
from .v1_fixes import install as _install_v1_fixes

_install_guardrails(_core)
_install_agility(_core)
_install_closure(_core)
_install_segmentation(_core)
_install_v1(_core)
_install_v1_fixes(_core)
_install_model_policy(_core)
_install_maintenance(_core)
_install_autonomy(_core)

from .mcp_model_policy import install as _install_mcp_model_policy

_install_mcp_model_policy()

from .mcp_maintenance import install as _install_mcp_maintenance

_install_mcp_maintenance()

from .mcp_autonomy import install as _install_mcp_autonomy

_install_mcp_autonomy()

del (
    _core,
    _install_guardrails,
    _install_agility,
    _install_closure,
    _install_segmentation,
    _install_v1,
    _install_v1_fixes,
    _install_model_policy,
    _install_maintenance,
    _install_autonomy,
    _install_mcp_model_policy,
    _install_mcp_maintenance,
    _install_mcp_autonomy,
)
