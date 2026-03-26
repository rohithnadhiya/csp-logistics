"""
CSP Variables and Domains for the Logistics Routing Problem.

The CSP is modeled as a multi-variable assignment problem:
  - Variable 1: ROUTE_CHOICE   -> which of the N OSRM alternatives to use
  - Variable 2: TIME_WINDOW    -> departure time band (early/mid/late)
  - Variable 3: VEHICLE_TYPE   -> bike | car | truck

The solver must assign values to all three variables such that
all constraints are satisfied, minimising a weighted cost function.
"""

from dataclasses import dataclass, field
from typing import List, Any, Dict


# -----------------------------------------------
# Domain values
# -----------------------------------------------

TIME_WINDOWS = [
    {"id": "early",  "label": "Early (06:00-10:00)", "traffic_factor": 1.2},
    {"id": "mid",    "label": "Mid   (10:00-16:00)", "traffic_factor": 1.6},
    {"id": "late",   "label": "Late  (16:00-20:00)", "traffic_factor": 1.8},
    {"id": "night",  "label": "Night (20:00-06:00)", "traffic_factor": 0.9},
]

VEHICLE_TYPES = [
    {"id": "bike",  "label": "Bike",  "speed_factor": 1.0,  "energy_per_km": 0.05, "capacity_kg": 30},
    {"id": "car",   "label": "Car",   "speed_factor": 1.2,  "energy_per_km": 0.12, "capacity_kg": 500},
    {"id": "truck", "label": "Truck", "speed_factor": 0.75, "energy_per_km": 0.35, "capacity_kg": 5000},
]


# -----------------------------------------------
# Dataclasses
# -----------------------------------------------

@dataclass
class RouteOption:
    """One OSRM route alternative, decorated with metadata."""
    index: int
    distance_m: float
    duration_s: float
    geometry: List[List[float]]
    waypoints: List[Dict]
    traffic_factor: float = 1.0
    weather_factor: float = 1.0

    @property
    def distance_km(self) -> float:
        return self.distance_m / 1000.0

    @property
    def base_eta_min(self) -> float:
        return self.duration_s / 60.0

    def effective_eta(self, traffic=None, weather=None) -> float:
        t = traffic if traffic is not None else self.traffic_factor
        w = weather if weather is not None else self.weather_factor
        return self.base_eta_min * t * w

    def to_dict(self) -> Dict:
        return {
            "index": self.index,
            "distance_km": round(self.distance_km, 2),
            "base_eta_min": round(self.base_eta_min, 2),
            "traffic_factor": round(self.traffic_factor, 3),
            "weather_factor": round(self.weather_factor, 3),
            "effective_eta_min": round(self.effective_eta(), 2),
            "geometry": self.geometry,
        }


@dataclass
class CSPVariable:
    """A single CSP variable with its name and mutable domain."""
    name: str
    domain: List[Any]
    assigned: Any = None

    def is_assigned(self) -> bool:
        return self.assigned is not None

    def remaining_domain(self) -> List[Any]:
        return self.domain if not self.is_assigned() else [self.assigned]


@dataclass
class CSPState:
    """Full assignment state passed between solver calls."""
    assignment: Dict = field(default_factory=dict)
    pruned: Dict = field(default_factory=dict)
    nodes_explored: int = 0
    constraint_checks: int = 0

    def copy(self):
        import copy
        return copy.deepcopy(self)
