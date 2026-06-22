"""Deployment-based aerodynamic effectiveness for dynamic V1."""

from __future__ import annotations

# V1 approximation: folded blade overlap/shadow reduces usable aero below open value.
FOLDED_MIN_AERO_EFFECTIVENESS = 0.35


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def deployment_progress_from_theta(
    theta_deg: float,
    *,
    theta_min_deg: float,
    theta_max_deg: float = 0.0,
) -> float:
    """Normalized hinge deployment progress in [0, 1] (0=folded, 1=open)."""
    span = theta_max_deg - theta_min_deg
    if abs(span) < 1e-12:
        return 1.0 if theta_deg >= theta_max_deg else 0.0
    return _clamp01((theta_deg - theta_min_deg) / span)


def aero_effectiveness_from_progress(
    deployment_progress_01: float,
    *,
    min_folded_effectiveness: float = FOLDED_MIN_AERO_EFFECTIVENESS,
) -> float:
    """Scale quasi-steady thrust/torque by deployment (V1 linear blend).

    At full fold (progress=0) aero uses ``min_folded_effectiveness`` (<1) so the
    folded configuration does not produce the same lift as fully deployed geometry.
    At full open (progress=1) effectiveness is 1.0.
    """
    progress = _clamp01(deployment_progress_01)
    floor = _clamp01(min_folded_effectiveness)
    return floor + progress * (1.0 - floor)
