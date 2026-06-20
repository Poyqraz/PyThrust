"""Simple forward-Euler integration helpers for dynamic spin-up."""

from __future__ import annotations


def euler_step(
    value: float,
    derivative: float,
    dt_s: float,
) -> float:
    """Advance one state variable by ``derivative * dt``."""
    return value + derivative * dt_s
