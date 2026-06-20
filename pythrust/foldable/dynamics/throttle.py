"""Configurable throttle profiles for dynamic spin-up."""

from __future__ import annotations

from typing import Literal

ThrottleProfileName = Literal["step", "linear_ramp"]


def throttle_at_time(
    time_s: float,
    *,
    profile: ThrottleProfileName = "step",
    ramp_time_s: float = 0.5,
) -> float:
    """Return throttle command in [0, 1] at ``time_s``.

    - ``step``: 0 at t=0, 1.0 for t>0 (backward-compatible default).
    - ``linear_ramp``: 0 at t=0, linear rise to 1.0 over ``ramp_time_s``.
    """
    if time_s <= 0.0:
        return 0.0
    if profile == "step":
        return 1.0
    if profile == "linear_ramp":
        if ramp_time_s <= 0.0:
            return 1.0
        return min(1.0, time_s / ramp_time_s)
    raise ValueError(f"Unknown throttle profile: {profile!r}")
