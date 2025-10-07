"""Graph structures representing the supply chain network."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, Iterable, List, Mapping, Optional

from .config import EdgeConfig, ScenarioConfig, TimeProfileConfig
from .exceptions import ConfigurationError
from .parameters import RoutingParameters


MINUTES_PER_DAY = 24 * 60


@dataclass
class TimeProfile:
    """Piecewise constant multiplier active on a time interval."""

    start_minute: int
    end_minute: int
    multiplier: float

    def contains(self, minute: int) -> bool:
        minute %= MINUTES_PER_DAY
        start = self.start_minute % MINUTES_PER_DAY
        end = self.end_minute % MINUTES_PER_DAY
        if start <= end:
            return start <= minute < end
        return minute >= start or minute < end


@dataclass
class Node:
    id: str
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    metadata: Dict[str, object] = field(default_factory=dict)


@dataclass
class Edge:
    source: str
    target: str
    length_km: float
    base_travel_time_hours: float
    fuel_cost_per_km: float
    loss_probability: float
    risk_factor: float
    time_profiles: List[TimeProfile] = field(default_factory=list)
    fuel_profiles: List[TimeProfile] = field(default_factory=list)
    loss_profiles: List[TimeProfile] = field(default_factory=list)
    risk_profiles: List[TimeProfile] = field(default_factory=list)
    restrictions: Dict[str, object] = field(default_factory=dict)

    def _multiplier(self, profiles: Iterable[TimeProfile], minute: int) -> float:
        for profile in profiles:
            if profile.contains(minute):
                return profile.multiplier
        return 1.0

    def travel_time_hours(self, departure_minute: int) -> float:
        multiplier = self._multiplier(self.time_profiles, departure_minute)
        return self.base_travel_time_hours * multiplier

    def fuel_cost(self, departure_minute: int) -> float:
        multiplier = self._multiplier(self.fuel_profiles, departure_minute)
        return self.length_km * self.fuel_cost_per_km * multiplier

    def loss_probability_at(self, departure_minute: int) -> float:
        multiplier = self._multiplier(self.loss_profiles, departure_minute)
        return self.loss_probability * multiplier

    def risk_factor_at(self, departure_minute: int) -> float:
        multiplier = self._multiplier(self.risk_profiles, departure_minute)
        return self.risk_factor * multiplier

    def travel_cost(self, parameters: RoutingParameters, departure_minute: int) -> float:
        travel_time = self.travel_time_hours(departure_minute)
        fuel_cost = self.fuel_cost(departure_minute)
        time_cost = travel_time * parameters.time_value_per_hour
        loss_cost = self.loss_probability_at(departure_minute) * parameters.loss_penalty
        risk_cost = self.risk_factor_at(departure_minute) * parameters.risk_penalty

        weights = parameters.weights
        return (
            weights.fuel * fuel_cost
            + weights.time * time_cost
            + weights.loss * loss_cost
            + weights.risk * risk_cost
        )


class Graph:
    """Directed graph describing the supply chain network."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, List[Edge]] = {}

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node
        self.edges.setdefault(node.id, [])

    def add_edge(self, edge: Edge) -> None:
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError("Both source and target nodes must be added before creating an edge")
        self.edges[edge.source].append(edge)

    def neighbors(self, node_id: str) -> Iterable[Edge]:
        return self.edges.get(node_id, [])

    def get_node(self, node_id: str) -> Node:
        return self.nodes[node_id]

    def estimate_travel_time(self, source_id: str, target_id: str, parameters: RoutingParameters) -> float:
        distance = self._haversine_distance_km(source_id, target_id)
        if distance is None:
            return 0.0
        speed = max(parameters.default_speed_kmph, 1.0)
        return distance / speed

    def _haversine_distance_km(self, source_id: str, target_id: str) -> Optional[float]:
        source = self.nodes.get(source_id)
        target = self.nodes.get(target_id)
        if not source or not target or source.latitude is None or source.longitude is None:
            return None
        if target.latitude is None or target.longitude is None:
            return None
        radius = 6371.0
        lat1 = radians(source.latitude)
        lon1 = radians(source.longitude)
        lat2 = radians(target.latitude)
        lon2 = radians(target.longitude)
        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1
        a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return radius * c


def parse_time_profiles(data: Iterable[TimeProfileConfig]) -> List[TimeProfile]:
    profiles: List[TimeProfile] = []
    for item in data:
        profiles.append(
            TimeProfile(
                start_minute=item.start_minute,
                end_minute=item.end_minute,
                multiplier=item.multiplier,
            )
        )
    return profiles


def build_graph(config: Mapping[str, object]) -> Graph:
    """Build a graph from a raw mapping for backwards compatibility."""

    scenario = ScenarioConfig.from_mapping(config)
    return build_graph_from_scenario(scenario)


def build_graph_from_scenario(scenario: ScenarioConfig) -> Graph:
    graph = Graph()

    for node_config in scenario.nodes:
        node = Node(
            id=node_config.id,
            name=node_config.name,
            latitude=node_config.latitude,
            longitude=node_config.longitude,
            metadata=dict(node_config.metadata),
        )
        graph.add_node(node)

    for edge_config in scenario.edges:
        _validate_edge(edge_config)
        edge = Edge(
            source=edge_config.source,
            target=edge_config.target,
            length_km=edge_config.length_km,
            base_travel_time_hours=edge_config.base_travel_time_hours,
            fuel_cost_per_km=edge_config.fuel_cost_per_km,
            loss_probability=edge_config.loss_probability,
            risk_factor=edge_config.risk_factor,
            time_profiles=parse_time_profiles(edge_config.time_profiles),
            fuel_profiles=parse_time_profiles(edge_config.fuel_profiles),
            loss_profiles=parse_time_profiles(edge_config.loss_profiles),
            risk_profiles=parse_time_profiles(edge_config.risk_profiles),
            restrictions=dict(edge_config.restrictions),
        )
        graph.add_edge(edge)

    return graph


def _validate_edge(edge: EdgeConfig) -> None:
    if edge.loss_probability > 1:
        raise ConfigurationError(
            f"Loss probability for edge {edge.source}->{edge.target} exceeds 1"
        )
    if edge.risk_factor > 1 and not edge.restrictions.get("allow_high_risk"):
        raise ConfigurationError(
            "High risk edges must explicitly set 'allow_high_risk': true in restrictions"
        )
