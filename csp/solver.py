"""
Core CSP Solver: Backtracking + MRV + LCV + Forward Checking + AC-3 Propagation
"""

import time
import copy
from typing import List, Dict, Optional, Tuple

from csp.variables import (
    RouteOption, TIME_WINDOWS, VEHICLE_TYPES,
    CSPVariable, CSPState,
)
from csp.constraints import evaluate_assignment, check_partial_consistency

VARIABLE_ORDER = ["route", "time_window", "vehicle"]


def _build_variables(routes):
    return {
        "route":       CSPVariable("route",       list(range(len(routes)))),
        "time_window": CSPVariable("time_window", list(range(len(TIME_WINDOWS)))),
        "vehicle":     CSPVariable("vehicle",     list(range(len(VEHICLE_TYPES)))),
    }


def _mrv_select_variable(variables, assignment, pruned):
    unassigned = [k for k in VARIABLE_ORDER if k not in assignment]
    if not unassigned:
        return None
    def remaining(k):
        p = set(pruned.get(k, []))
        return [v for v in variables[k].domain if v not in p]
    return min(unassigned, key=lambda k: len(remaining(k)))


def _lcv_order_values(var, domain, assignment, routes, weather_factor, cfg, state):
    def penalty_for(v):
        trial = dict(assignment)
        trial[var] = v
        r  = routes[trial.get("route", 0)] if "route" in trial else routes[0]
        tw = TIME_WINDOWS[trial.get("time_window", 0)] if "time_window" in trial else TIME_WINDOWS[0]
        vh = VEHICLE_TYPES[trial.get("vehicle", 0)] if "vehicle" in trial else VEHICLE_TYPES[0]
        state.constraint_checks += 1
        res = evaluate_assignment(r, tw, vh, weather_factor, cfg)
        return res["total_penalty"]
    return sorted(domain, key=penalty_for)


def _forward_check(var, value, assignment, variables, pruned, routes, weather_factor, cfg, state):
    trial = dict(assignment)
    trial[var] = value
    future_vars = [k for k in VARIABLE_ORDER if k not in trial]
    for fv in future_vars:
        p_set = set(pruned.get(fv, []))
        valid_count = 0
        for fval in variables[fv].domain:
            if fval in p_set:
                continue
            probe = dict(trial)
            probe[fv] = fval
            state.constraint_checks += 1
            ok, _ = check_partial_consistency(probe, routes, weather_factor, cfg)
            if ok:
                valid_count += 1
            else:
                pruned.setdefault(fv, []).append(fval)
        if valid_count == 0:
            return False
    return True


def _ac3(variables, routes, weather_factor, cfg, state):
    pruned = {}
    queue = [(a, b) for a in VARIABLE_ORDER for b in VARIABLE_ORDER if a != b]

    def revise(xi, xj):
        revised = False
        xi_pruned = set(pruned.get(xi, []))
        xj_pruned = set(pruned.get(xj, []))
        removals = []
        for xi_val in variables[xi].domain:
            if xi_val in xi_pruned:
                continue
            supported = False
            for xj_val in variables[xj].domain:
                if xj_val in xj_pruned:
                    continue
                probe = {xi: xi_val, xj: xj_val}
                r  = routes[probe.get("route", 0)]
                tw = TIME_WINDOWS[probe.get("time_window", 0)]
                vh = VEHICLE_TYPES[probe.get("vehicle", 0)]
                state.constraint_checks += 1
                result = evaluate_assignment(r, tw, vh, weather_factor, cfg)
                if result["total_penalty"] < 2.0:
                    supported = True
                    break
            if not supported:
                removals.append(xi_val)
                revised = True
        for v in removals:
            pruned.setdefault(xi, []).append(v)
        return revised

    while queue:
        xi, xj = queue.pop(0)
        if revise(xi, xj):
            xi_remaining = [v for v in variables[xi].domain if v not in set(pruned.get(xi, []))]
            if not xi_remaining:
                return False, pruned
            for xk in VARIABLE_ORDER:
                if xk != xi and xk != xj:
                    queue.append((xk, xi))
    return True, pruned


def _backtrack(assignment, variables, pruned, routes, weather_factor, cfg, state, best,
               use_mrv=True, use_lcv=True, use_fc=True):
    state.nodes_explored += 1
    if len(assignment) == len(VARIABLE_ORDER):
        r  = routes[assignment["route"]]
        tw = TIME_WINDOWS[assignment["time_window"]]
        vh = VEHICLE_TYPES[assignment["vehicle"]]
        state.constraint_checks += 1
        result = evaluate_assignment(r, tw, vh, weather_factor, cfg)
        if result["satisfied"]:
            if best.get("cost") is None or result["cost"] < best["cost"]:
                best["assignment"] = dict(assignment)
                best["cost"]       = result["cost"]
                best["result"]     = result
        return True

    if use_mrv:
        var = _mrv_select_variable(variables, assignment, pruned)
    else:
        unassigned = [k for k in VARIABLE_ORDER if k not in assignment]
        var = unassigned[0] if unassigned else None

    if var is None:
        return False

    p_set  = set(pruned.get(var, []))
    domain = [v for v in variables[var].domain if v not in p_set]

    if use_lcv:
        domain = _lcv_order_values(var, domain, assignment, routes, weather_factor, cfg, state)

    for value in domain:
        assignment[var] = value
        saved_pruned    = copy.deepcopy(pruned)
        fc_ok = True
        if use_fc:
            fc_ok = _forward_check(var, value, assignment, variables, pruned, routes, weather_factor, cfg, state)
        if fc_ok:
            _backtrack(assignment, variables, pruned, routes, weather_factor, cfg, state, best, use_mrv, use_lcv, use_fc)
        del assignment[var]
        pruned.clear()
        pruned.update(saved_pruned)
    return best.get("assignment") is not None


def solve_csp(routes, weather_factor=1.0, cfg=None, use_mrv=True, use_lcv=True,
              use_fc=True, use_propagation=True):
    if cfg is None:
        cfg = {}
    t0 = time.perf_counter()
    variables = _build_variables(routes)
    state     = CSPState()
    pruned    = {}
    steps     = []

    steps.append("Initialised CSP variables: ROUTE_CHOICE x TIME_WINDOW x VEHICLE_TYPE")
    steps.append(f"Domain sizes: routes={len(routes)}, time_windows={len(TIME_WINDOWS)}, vehicles={len(VEHICLE_TYPES)}")

    if use_propagation:
        consistent, pruned = _ac3(variables, routes, weather_factor, cfg, state)
        steps.append(f"AC-3 propagation complete - pruned {sum(len(v) for v in pruned.values())} values")
        if not consistent:
            steps.append("AC-3 detected inconsistency - relaxing constraints")
            pruned = {}

    steps.append(f"Backtracking search started (MRV={use_mrv}, LCV={use_lcv}, FC={use_fc})")
    best = {}
    _backtrack({}, variables, pruned, routes, weather_factor, cfg, state, best, use_mrv, use_lcv, use_fc)
    elapsed = round((time.perf_counter() - t0) * 1000, 3)

    if not best.get("assignment"):
        steps.append("No fully satisfying assignment - selecting minimum-cost option")
        best_cost = None
        for ri in range(len(routes)):
            for ti in range(len(TIME_WINDOWS)):
                for vi in range(len(VEHICLE_TYPES)):
                    r  = routes[ri]; tw = TIME_WINDOWS[ti]; vh = VEHICLE_TYPES[vi]
                    state.constraint_checks += 1
                    res = evaluate_assignment(r, tw, vh, weather_factor, cfg)
                    if best_cost is None or res["cost"] < best_cost:
                        best_cost = res["cost"]
                        best["assignment"] = {"route": ri, "time_window": ti, "vehicle": vi}
                        best["cost"] = res["cost"]
                        best["result"] = res

    assignment = best["assignment"]
    result     = best["result"]
    sel_route  = routes[assignment["route"]]
    sel_tw     = TIME_WINDOWS[assignment["time_window"]]
    sel_vh     = VEHICLE_TYPES[assignment["vehicle"]]

    traffic_f = sel_tw["traffic_factor"]
    speed_f   = sel_vh["speed_factor"]
    eff_eta   = round(sel_route.base_eta_min * traffic_f * weather_factor / speed_f, 1)

    steps.append(f"Best assignment: Route #{assignment['route']} | {sel_tw['label']} | {sel_vh['label']}")
    steps.append(f"Distance: {sel_route.distance_km:.1f} km | Effective ETA: {eff_eta} min")
    steps.append(f"Weather factor: {weather_factor:.2f} | Traffic factor: {traffic_f:.2f}")

    constraint_summary = [
        f"{'OK' if c['satisfied'] else 'FAIL'} {c['name'].upper()}: {c['msg']}"
        for c in result["details"]
    ]

    all_scores = []
    for i, r in enumerate(routes):
        res = evaluate_assignment(r, sel_tw, sel_vh, weather_factor, cfg)
        all_scores.append({
            "route_index":    i,
            "distance_km":    round(r.distance_km, 2),
            "eta_min":        round(r.base_eta_min * traffic_f * weather_factor / speed_f, 1),
            "cost":           res["cost"],
            "satisfied":      res["satisfied"],
            "geometry":       r.geometry,
            "traffic_factor": r.traffic_factor,
            "weather_factor": weather_factor,
        })

    algo_name = ("CSP Backtracking"
                 + (" + MRV" if use_mrv else "")
                 + (" + LCV" if use_lcv else "")
                 + (" + FC"  if use_fc  else "")
                 + (" + AC-3" if use_propagation else ""))

    return {
        "algorithm":          algo_name,
        "selected_route":     assignment["route"],
        "selected_time":      sel_tw["label"],
        "selected_vehicle":   sel_vh["label"],
        "distance_km":        round(sel_route.distance_km, 2),
        "effective_eta_min":  eff_eta,
        "weather_factor":     weather_factor,
        "traffic_factor":     traffic_f,
        "nodes_explored":     state.nodes_explored,
        "constraint_checks":  state.constraint_checks,
        "execution_time_ms":  elapsed,
        "cost":               round(best["cost"], 4),
        "satisfied":          result["satisfied"],
        "constraint_details": result["details"],
        "all_routes":         all_scores,
        "geometry":           sel_route.geometry,
        "steps":              steps,
        "constraint_summary": constraint_summary,
        "rationale": (
            f"Route #{assignment['route']} selected via CSP. "
            f"Distance {sel_route.distance_km:.1f} km, effective ETA {eff_eta} min "
            f"(weather x{weather_factor:.2f}, traffic x{traffic_f:.2f}, {sel_vh['label']}). "
            f"All {len(result['details'])} constraints evaluated in {elapsed} ms "
            f"after exploring {state.nodes_explored} nodes."
        ),
    }
