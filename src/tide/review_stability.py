from __future__ import annotations

from types import ModuleType

from . import session_stability as _session_stability


def install(core: ModuleType) -> None:
    if getattr(core, "_review_core_stability_installed", False):
        return
    original = _session_stability._ORIGINALS.get("submit_review")
    if original is None:
        raise RuntimeError("Tide session stability must be installed before review stability")
    core.submit_review = original
    core._review_core_stability_installed = True
