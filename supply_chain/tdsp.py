"""Implementation of a time-dependent A* routing algorithm."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from math import inf
from typing import Dict, Iterable, List, Optional, Tuple

from .graph import Edge, Graph, MINUTES_PER_DAY
from .parameters import RoutingParameters


@dataclass
class RouteStep:
    node_id: str
    arrival_minute: int


@dataclass
class RouteResult:
    total_cost: float
    total_travel_time_hours: float
    path: List[RouteStep]

    def as_dict(self) -> dict:
        return {
            "total_cost": self.total_cost,
            "total_travel_time_hours": self.total_travel_time_hours,
            "path": [
                {"node_id": step.node_id, "arrival_minute": step.arrival_minute}
                for step in self.path
            ],
        }


def tdsp_a_star(
    graph: Graph,
    start: str,
    goal: str,
    departure_minute: int,
    parameters: RoutingParameters,
) -> Optional[RouteResult]:
    """Find a least-cost path using an A* variant aware of time-dependent edges."""

    open_set: List[Tuple[float, float, str, int]] = []
    heapq.heappush(open_set, (0.0, 0.0, start, departure_minute))

    g_score: Dict[str, float] = {start: 0.0}
    arrival_time: Dict[str, int] = {start: departure_minute}
    came_from: Dict[str, Tuple[str, int]] = {}

    best_total_time: Dict[str, float] = {start: 0.0}

    while open_set:
        priority, current_cost, current_node, current_departure = heapq.heappop(open_set)

        if current_node == goal:
            return _reconstruct_path(
                came_from,
                goal,
                arrival_time[goal],
                current_cost,
                best_total_time[goal],
            )

        for edge in graph.neighbors(current_node):
            travel_time = edge.travel_time_hours(current_departure)
            travel_minutes = max(int(round(travel_time * 60)), 1)
            arrival = (current_departure + travel_minutes) % MINUTES_PER_DAY
            tentative_cost = current_cost + edge.travel_cost(parameters, current_departure)
            tentative_time = best_total_time[current_node] + travel_time

            previous_cost = g_score.get(edge.target, inf)
            if tentative_cost + 1e-9 < previous_cost:
                g_score[edge.target] = tentative_cost
                arrival_time[edge.target] = arrival
                came_from[edge.target] = (current_node, arrival)
                best_total_time[edge.target] = tentative_time
                heuristic = graph.estimate_travel_time(edge.target, goal, parameters)
                heapq.heappush(
                    open_set,
                    (
                        tentative_cost + heuristic,
                        tentative_cost,
                        edge.target,
                        arrival,
                    ),
                )

    return None


def _reconstruct_path(
    came_from: Dict[str, Tuple[str, int]],
    goal: str,
    arrival_minute: int,
    total_cost: float,
    total_travel_time_hours: float,
) -> RouteResult:
    path: List[RouteStep] = [RouteStep(node_id=goal, arrival_minute=arrival_minute)]
    current = goal
    while current in came_from:
        previous, arrival = came_from[current]
        path.append(RouteStep(node_id=previous, arrival_minute=arrival))
        current = previous
    path.reverse()
    return RouteResult(
        total_cost=total_cost,
        total_travel_time_hours=total_travel_time_hours,
        path=path,
    )
