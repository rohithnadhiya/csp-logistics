"""
Baseline search algorithms: BFS, DFS, Greedy, Branch and Bound.
"""

import time
from collections import deque
from typing import List, Dict, Optional, Tuple

from csp.variables import RouteOption, TIME_WINDOWS, VEHICLE_TYPES
from csp.constraints import evaluate_assignment

_DEFAULT_TW = TIME_WINDOWS[1]
_DEFAULT_VH = VEHICLE_TYPES[1]


def _score(route, weather_factor, cfg):
    res = evaluate_assignment(route, _DEFAULT_TW, _DEFAULT_VH, weather_factor, cfg)
    return res["satisfied"], res["cost"], res


def bfs_solve(routes, weather_factor=1.0, cfg=None):
    if cfg is None: cfg = {}
    t0 = time.perf_counter()
    nodes_explored = 0; constraint_checks = 0
    best = None; best_cost = float("inf")
    queue = deque(routes)
    while queue:
        route = queue.popleft()
        nodes_explored += 1; constraint_checks += 1
        ok, cost, res = _score(route, weather_factor, cfg)
        if ok and cost < best_cost:
            best_cost = cost; best = (route, res)
    return _build_result("BFS", best, best_cost, nodes_explored, constraint_checks,
                         round((time.perf_counter()-t0)*1000, 3), routes, weather_factor, cfg)


def dfs_solve(routes, weather_factor=1.0, cfg=None):
    if cfg is None: cfg = {}
    t0 = time.perf_counter()
    nodes_explored = 0; constraint_checks = 0
    best = None; best_cost = float("inf")
    stack = list(routes)[::-1]
    while stack:
        route = stack.pop()
        nodes_explored += 1; constraint_checks += 1
        ok, cost, res = _score(route, weather_factor, cfg)
        if ok and cost < best_cost:
            best_cost = cost; best = (route, res)
    return _build_result("DFS", best, best_cost, nodes_explored, constraint_checks,
                         round((time.perf_counter()-t0)*1000, 3), routes, weather_factor, cfg)


def greedy_solve(routes, weather_factor=1.0, cfg=None):
    if cfg is None: cfg = {}
    t0 = time.perf_counter()
    nodes_explored = 0; constraint_checks = 0
    scored = []
    for route in routes:
        nodes_explored += 1; constraint_checks += 1
        ok, cost, res = _score(route, weather_factor, cfg)
        scored.append((cost, ok, route, res))
    scored.sort(key=lambda x: x[0])
    best = None; best_cost = float("inf")
    for cost, ok, route, res in scored:
        nodes_explored += 1
        if ok:
            best = (route, res); best_cost = cost; break
    if best is None and scored:
        _, _, route, res = scored[0]
        best = (route, res); best_cost = scored[0][0]
    return _build_result("Greedy", best, best_cost, nodes_explored, constraint_checks,
                         round((time.perf_counter()-t0)*1000, 3), routes, weather_factor, cfg)


def branch_and_bound_solve(routes, weather_factor=1.0, cfg=None):
    if cfg is None: cfg = {}
    t0 = time.perf_counter()
    nodes_explored = 0; constraint_checks = 0
    best_cost = float("inf"); best = None
    open_list = sorted(
        [(r.distance_km * 0.4 + r.base_eta_min * 0.4, r) for r in routes],
        key=lambda x: x[0]
    )
    while open_list:
        lb, route = open_list.pop(0)
        nodes_explored += 1
        if lb >= best_cost:
            continue
        constraint_checks += 1
        ok, cost, res = _score(route, weather_factor, cfg)
        if cost < best_cost:
            best_cost = cost; best = (route, res)
    return _build_result("Branch & Bound", best, best_cost, nodes_explored, constraint_checks,
                         round((time.perf_counter()-t0)*1000, 3), routes, weather_factor, cfg)


def _build_result(algo_name, best, best_cost, nodes_explored, constraint_checks,
                  elapsed, routes, weather_factor, cfg):
    if best is None:
        route = routes[0]; _, _, res = _score(route, weather_factor, cfg)
    else:
        route, res = best

    tf  = _DEFAULT_TW["traffic_factor"]
    sf  = _DEFAULT_VH["speed_factor"]
    eta = round(route.base_eta_min * tf * weather_factor / sf, 1)

    all_scores = []
    for i, r in enumerate(routes):
        _, cost, _ = _score(r, weather_factor, cfg)
        all_scores.append({
            "route_index":    i,
            "distance_km":    round(r.distance_km, 2),
            "eta_min":        round(r.base_eta_min * tf * weather_factor / sf, 1),
            "cost":           cost,
            "satisfied":      True,
            "geometry":       r.geometry,
            "traffic_factor": r.traffic_factor,
            "weather_factor": weather_factor,
        })

    return {
        "algorithm":          algo_name,
        "selected_route":     route.index,
        "selected_time":      _DEFAULT_TW["label"],
        "selected_vehicle":   _DEFAULT_VH["label"],
        "distance_km":        round(route.distance_km, 2),
        "effective_eta_min":  eta,
        "weather_factor":     weather_factor,
        "traffic_factor":     tf,
        "nodes_explored":     nodes_explored,
        "constraint_checks":  constraint_checks,
        "execution_time_ms":  elapsed,
        "cost":               round(best_cost if best_cost < 1e9 else res.get("cost", 0), 4),
        "satisfied":          best is not None,
        "constraint_details": res["details"],
        "all_routes":         all_scores,
        "geometry":           route.geometry,
        "steps":              [f"{algo_name} scanned {nodes_explored} nodes, {constraint_checks} constraint checks"],
        "constraint_summary": [f"{'OK' if c['satisfied'] else 'FAIL'} {c['name'].upper()}: {c['msg']}" for c in res["details"]],
        "rationale": (
            f"{algo_name} selected Route #{route.index}. "
            f"Distance {route.distance_km:.1f} km, ETA {eta} min. "
            f"Explored {nodes_explored} nodes in {elapsed} ms."
        ),
    }
