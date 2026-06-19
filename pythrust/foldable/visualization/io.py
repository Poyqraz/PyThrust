"""Load and join foldable CSV outputs into visualization states."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from ..summary import THROTTLE_TOLERANCE
from .state import PropellerVisualState

DEFAULT_OPEN_DIAMETER_M = 0.25
DEFAULT_THETA_MIN_DEG = -45.0
DEFAULT_BLADE_COUNT = 2


def _read_csv_rows(path: str | Path) -> List[Dict[str, str]]:
    csv_path = Path(path)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Empty or invalid CSV: {csv_path}")
        return [dict(row) for row in reader]


def read_variant_parameters_csv(path: str | Path) -> Dict[str, Dict[str, Any]]:
    """Load per-variant physical parameters keyed by variant_id."""
    rows = _read_csv_rows(path)
    return {
        str(row["variant_id"]): {
            "root_ratio": int(row["root_ratio"]),
            "tip_ratio": int(row["tip_ratio"]),
            "tip_length_m": float(row["tip_length_m"]),
            "tip_mass_kg": float(row["tip_mass_kg"]),
            "tip_segment_cg_from_hinge_m": float(row["tip_segment_cg_from_hinge_m"]),
            "hinge_radius_m": float(row["hinge_radius_m"]),
            "hinge_stiffness_nm_per_rad": float(row["hinge_stiffness_nm_per_rad"]),
            "hinge_friction_nm": float(row["hinge_friction_nm"]),
        }
        for row in rows
    }


def _throttle_key(throttle: float) -> float:
    return round(throttle, 4)


def _index_by_variant_throttle(
    rows: Sequence[Mapping[str, Any]],
    *,
    throttle_field: str = "throttle",
) -> Dict[tuple[str, float], Dict[str, Any]]:
    indexed: Dict[tuple[str, float], Dict[str, Any]] = {}
    for row in rows:
        variant_id = str(row["variant_id"])
        throttle = float(row[throttle_field])
        indexed[(variant_id, _throttle_key(throttle))] = dict(row)
    return indexed


def _hinge_position_from_params(
    params: Mapping[str, Any],
    *,
    diameter_open_m: float,
) -> float:
    open_radius_m = diameter_open_m / 2.0
    return open_radius_m * int(params["root_ratio"]) / 100.0


def _build_state(
    variant_id: str,
    throttle: float,
    *,
    sweep_row: Mapping[str, Any] | None,
    moment_row: Mapping[str, Any] | None,
    params: Mapping[str, Any],
    diameter_open_m: float = DEFAULT_OPEN_DIAMETER_M,
    stowed_envelope_diameter_m: float | None = None,
    theta_min_deg: float = DEFAULT_THETA_MIN_DEG,
    blade_count: int = DEFAULT_BLADE_COUNT,
) -> PropellerVisualState:
    if sweep_row is None and moment_row is None:
        raise ValueError(f"No data for {variant_id} at throttle {throttle}")

    ref_row: Mapping[str, Any] = sweep_row or moment_row  # type: ignore[assignment]
    root_ratio = int(ref_row.get("root_ratio", params["root_ratio"]))
    tip_ratio = int(ref_row.get("tip_ratio", params["tip_ratio"]))

    hinge_position_m = _hinge_position_from_params(
        params,
        diameter_open_m=diameter_open_m,
    )
    tip_segment_length_m = float(params["tip_length_m"])

    rpm = float(moment_row["rpm"]) if moment_row else float(sweep_row["rpm"])  # type: ignore[index]
    theta_deg = (
        float(moment_row["theta_deg"])
        if moment_row
        else float(sweep_row["theta_deg"])  # type: ignore[index]
    )
    effective_diameter_m = (
        float(moment_row["effective_diameter_m"])
        if moment_row
        else float(sweep_row["effective_diameter_m"])  # type: ignore[index]
    )
    opening_moment_nm = float(moment_row["opening_moment_nm"]) if moment_row else 0.0
    resisting_moment_nm = float(moment_row["resisting_moment_nm"]) if moment_row else 0.0
    moment_margin_nm = float(moment_row["moment_margin_nm"]) if moment_row else 0.0
    hinge_state = str(moment_row["hinge_state"]) if moment_row else "folded"
    foldable_thrust_n = (
        float(sweep_row["foldable_thrust_n"])
        if sweep_row
        else 0.0
    )

    return PropellerVisualState(
        variant_id=variant_id,
        root_ratio=root_ratio,
        tip_ratio=tip_ratio,
        throttle=throttle,
        rpm=rpm,
        theta_deg=theta_deg,
        effective_diameter_m=effective_diameter_m,
        opening_moment_nm=opening_moment_nm,
        resisting_moment_nm=resisting_moment_nm,
        moment_margin_nm=moment_margin_nm,
        hinge_state=hinge_state,
        foldable_thrust_n=foldable_thrust_n,
        hinge_position_m=hinge_position_m,
        tip_segment_length_m=tip_segment_length_m,
        diameter_open_m=diameter_open_m,
        stowed_envelope_diameter_m=stowed_envelope_diameter_m,
        blade_count=blade_count,
        theta_min_deg=theta_min_deg,
    )


def _synthesize_throttle_zero_row(
    variant_id: str,
    sweep_rows: Sequence[Mapping[str, Any]],
    *,
    diameter_open_m: float,
    theta_min_deg: float,
) -> Dict[str, Any]:
    variant_rows = [row for row in sweep_rows if str(row["variant_id"]) == variant_id]
    if not variant_rows:
        raise ValueError(f"No sweep rows for variant {variant_id}")
    sample = variant_rows[0]
    compactness_ratio = float(sample["compactness_ratio"])
    folded_diameter_m = compactness_ratio * diameter_open_m
    return {
        "variant_id": variant_id,
        "root_ratio": int(sample["root_ratio"]),
        "tip_ratio": int(sample["tip_ratio"]),
        "throttle": 0.0,
        "rpm": 0.0,
        "theta_deg": theta_min_deg,
        "effective_diameter_m": folded_diameter_m,
        "foldable_thrust_n": 0.0,
        "opening_moment_nm": 0.0,
        "resisting_moment_nm": 0.0,
        "moment_margin_nm": 0.0,
        "hinge_state": "folded",
    }


def join_visual_states(
    sweep_path: str | Path,
    moment_path: str | Path,
    params_path: str | Path,
    *,
    throttle_values: Sequence[float] | None = None,
    diameter_open_m: float = DEFAULT_OPEN_DIAMETER_M,
    stowed_envelope_diameter_m: float | None = None,
    theta_min_deg: float = DEFAULT_THETA_MIN_DEG,
    blade_count: int = DEFAULT_BLADE_COUNT,
) -> List[PropellerVisualState]:
    """Join sweep, moment validation, and geometry parameter CSVs."""
    sweep_rows = _read_csv_rows(sweep_path)
    moment_rows = _read_csv_rows(moment_path)
    params_by_variant = read_variant_parameters_csv(params_path)

    sweep_index = _index_by_variant_throttle(sweep_rows)
    moment_index = _index_by_variant_throttle(moment_rows)

    if throttle_values is None:
        throttle_set = {
            float(row["throttle"]) for row in sweep_rows
        } | {
            float(row["throttle"]) for row in moment_rows
        }
        throttle_values = sorted(throttle_set)

    states: List[PropellerVisualState] = []
    for variant_id in sorted(params_by_variant):
        params = params_by_variant[variant_id]
        for throttle in throttle_values:
            key = (variant_id, _throttle_key(throttle))
            sweep_row = sweep_index.get(key)
            moment_row = moment_index.get(key)

            if abs(throttle) <= THROTTLE_TOLERANCE:
                synthetic = _synthesize_throttle_zero_row(
                    variant_id,
                    sweep_rows,
                    diameter_open_m=diameter_open_m,
                    theta_min_deg=theta_min_deg,
                )
                sweep_row = synthetic
                moment_row = synthetic

            if sweep_row is None and moment_row is None:
                continue

            states.append(
                _build_state(
                    variant_id,
                    throttle,
                    sweep_row=sweep_row,
                    moment_row=moment_row,
                    params=params,
                    diameter_open_m=diameter_open_m,
                    stowed_envelope_diameter_m=stowed_envelope_diameter_m,
                    theta_min_deg=theta_min_deg,
                    blade_count=blade_count,
                )
            )

    return states


def state_for(
    states: Sequence[PropellerVisualState],
    variant_id: str,
    throttle: float,
) -> PropellerVisualState:
    """Pick one state from a joined list."""
    for state in states:
        if state.variant_id == variant_id and abs(state.throttle - throttle) <= THROTTLE_TOLERANCE:
            return state
    raise KeyError(f"No visual state for {variant_id} at throttle {throttle}")
