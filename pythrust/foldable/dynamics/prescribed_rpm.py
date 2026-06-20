"""Prescribed RPM profiles for propeller-first physics validation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Literal, Sequence

RpmMode = Literal["constant", "profile", "ramp"]


def rpm_constant(_time_s: float, *, rpm: float) -> float:
    return max(0.0, rpm)


def rpm_ramp(
    time_s: float,
    *,
    rpm_start: float,
    rpm_end: float,
    ramp_time_s: float,
) -> float:
    if ramp_time_s <= 0.0:
        return max(0.0, rpm_end)
    if time_s <= 0.0:
        return max(0.0, rpm_start)
    fraction = min(1.0, time_s / ramp_time_s)
    return max(0.0, rpm_start + fraction * (rpm_end - rpm_start))


def rpm_from_arrays(
    time_s: float,
    times: Sequence[float],
    rpms: Sequence[float],
) -> float:
    """Piecewise linear interpolation from (times, rpms) arrays."""
    if not times or not rpms or len(times) != len(rpms):
        return 0.0
    if time_s <= times[0]:
        return max(0.0, rpms[0])
    if time_s >= times[-1]:
        return max(0.0, rpms[-1])
    for t0, t1, r0, r1 in zip(times, times[1:], rpms, rpms[1:]):
        if t0 <= time_s <= t1:
            span = t1 - t0
            if span <= 0.0:
                return max(0.0, r1)
            fraction = (time_s - t0) / span
            return max(0.0, r0 + fraction * (r1 - r0))
    return max(0.0, rpms[-1])


@dataclass(frozen=True)
class PrescribedRpmConfig:
    """Time-stepping and RPM prescription for physics path."""

    dt_s: float = 0.001
    t_end_s: float = 3.0
    rho_kg_m3: float = 1.225
    rpm_mode: RpmMode = "constant"
    constant_rpm: float = 7100.0
    ramp_rpm_start: float = 0.0
    ramp_rpm_end: float = 7100.0
    ramp_time_s: float = 0.5
    profile_times_s: tuple[float, ...] | None = None
    profile_rpms: tuple[float, ...] | None = None

    def build_schedule(self) -> Callable[[float], float]:
        if self.rpm_mode == "constant":
            rpm = self.constant_rpm
            return lambda t: rpm_constant(t, rpm=rpm)
        if self.rpm_mode == "ramp":
            return lambda t: rpm_ramp(
                t,
                rpm_start=self.ramp_rpm_start,
                rpm_end=self.ramp_rpm_end,
                ramp_time_s=self.ramp_time_s,
            )
        if self.rpm_mode == "profile":
            times = self.profile_times_s or (0.0, self.t_end_s)
            rpms = self.profile_rpms or (0.0, self.constant_rpm)
            return lambda t: rpm_from_arrays(t, times, rpms)
        raise ValueError(f"Unknown rpm_mode: {self.rpm_mode!r}")
