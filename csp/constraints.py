"""
Constraint functions for the logistics CSP.

Each constraint returns: (satisfied: bool, penalty: float, reason: str)
"""

from typing import Dict, Tuple

DEFAULT_MAX_DISTANCE_KM   = 100.0
DEFAULT_MAX_ETA_MIN        = 120.0
DEFAULT_ENERGY_BUDGET      = 50.0
DEFAULT_WEATHER_THRESHOLD  = 1.4
DEFAULT_TRAFFIC_THRESHOLD  = 1.7


def distance_constraint(route, max_km=DEFAULT_MAX_DISTANCE_KM):
    if route.distance_km <= max_km:
        return True, 0.0, f"Distance {route.distance_km:.1f} km <= {max_km} km OK"
    penalty = (route.distance_km - max_km) / max_km
    return False, penalty, f"Distance {route.distance_km:.1f} km > {max_km} km FAIL"


def eta_constraint(route, time_window, vehicle, weather_factor, max_min=DEFAULT_MAX_ETA_MIN):
    traffic = time_window["traffic_factor"]
    speed   = vehicle["speed_factor"]
    effective = route.base_eta_min * traffic * weather_factor / speed
    if effective <= max_min:
        return True, 0.0, f"ETA {effective:.1f} min <= {max_min} min OK"
    penalty = (effective - max_min) / max_min
    return False, penalty, f"ETA {effective:.1f} min > {max_min} min FAIL"


def weather_constraint(weather_factor, threshold=DEFAULT_WEATHER_THRESHOLD):
    if weather_factor <= threshold:
        return True, 0.0, f"Weather factor {weather_factor:.2f} <= {threshold} OK"
    penalty = (weather_factor - threshold) / threshold
    return False, penalty, f"Weather factor {weather_factor:.2f} > {threshold} (heavy rain) FAIL"


def traffic_constraint(time_window, threshold=DEFAULT_TRAFFIC_THRESHOLD):
    tf = time_window["traffic_factor"]
    if tf <= threshold:
        return True, 0.0, f"Traffic factor {tf:.2f} <= {threshold} OK"
    penalty = (tf - threshold) / threshold
    return False, penalty, f"Traffic factor {tf:.2f} > {threshold} (peak hour) FAIL"


def energy_constraint(route, vehicle, budget=DEFAULT_ENERGY_BUDGET):
    consumed = route.distance_km * vehicle["energy_per_km"]
    if consumed <= budget:
        return True, 0.0, f"Energy {consumed:.2f} <= {budget} units OK"
    penalty = (consumed - budget) / budget
    return False, penalty, f"Energy {consumed:.2f} > {budget} units FAIL"


CONSTRAINT_REGISTRY = ["distance", "eta", "weather", "traffic", "energy"]


def evaluate_assignment(route, time_window, vehicle, weather_factor, cfg=None):
    if cfg is None:
        cfg = {}
    checks = []

    ok, p, msg = distance_constraint(route, cfg.get("max_km", DEFAULT_MAX_DISTANCE_KM))
    checks.append({"name": "distance", "satisfied": ok, "penalty": p, "msg": msg})

    ok, p, msg = eta_constraint(route, time_window, vehicle, weather_factor,
                                cfg.get("max_eta_min", DEFAULT_MAX_ETA_MIN))
    checks.append({"name": "eta", "satisfied": ok, "penalty": p, "msg": msg})

    ok, p, msg = weather_constraint(weather_factor, cfg.get("weather_threshold", DEFAULT_WEATHER_THRESHOLD))
    checks.append({"name": "weather", "satisfied": ok, "penalty": p, "msg": msg})

    ok, p, msg = traffic_constraint(time_window, cfg.get("traffic_threshold", DEFAULT_TRAFFIC_THRESHOLD))
    checks.append({"name": "traffic", "satisfied": ok, "penalty": p, "msg": msg})

    ok, p, msg = energy_constraint(route, vehicle, cfg.get("energy_budget", DEFAULT_ENERGY_BUDGET))
    checks.append({"name": "energy", "satisfied": ok, "penalty": p, "msg": msg})

    satisfied = all(c["satisfied"] for c in checks)
    total_penalty = sum(c["penalty"] for c in checks)

    traffic_f = time_window["traffic_factor"]
    speed_f   = vehicle["speed_factor"]
    cost = (
        route.distance_km * 0.4 +
        route.base_eta_min * traffic_f * weather_factor / speed_f * 0.4 +
        route.distance_km * vehicle["energy_per_km"] * 0.2
    )

    return {
        "satisfied": satisfied,
        "total_penalty": round(total_penalty, 4),
        "cost": round(cost, 4),
        "details": checks,
    }


def check_partial_consistency(probe, routes, weather_factor, cfg=None):
    """
    Forward-checking helper: given a partial probe dict of integer indices,
    verify already-assigned variables are mutually consistent.
    """
    if cfg is None:
        cfg = {}
    penalty = 0.0

    from csp.variables import TIME_WINDOWS, VEHICLE_TYPES
    r_idx  = probe.get("route")
    tw_idx = probe.get("time_window")
    vh_idx = probe.get("vehicle")

    r  = routes[r_idx]        if r_idx  is not None else None
    tw = TIME_WINDOWS[tw_idx] if tw_idx is not None else None
    vh = VEHICLE_TYPES[vh_idx] if vh_idx is not None else None

    if r is not None:
        ok, p, _ = distance_constraint(r, cfg.get("max_km", DEFAULT_MAX_DISTANCE_KM))
        if not ok:
            return False, p
        penalty += p

    if r is not None and tw is not None and vh is not None:
        ok, p, _ = eta_constraint(r, tw, vh, weather_factor,
                                  cfg.get("max_eta_min", DEFAULT_MAX_ETA_MIN))
        if not ok:
            return False, p
        penalty += p

    return True, penalty
