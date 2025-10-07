"""Configuration models and validation utilities for routing scenarios."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Mapping, MutableMapping, Sequence

from .exceptions import ConfigurationError


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConfigurationError(message)


def _get(mapping: Mapping[str, object], key: str, default: object | None = None) -> object:
    if key not in mapping:
        if default is not None:
            return default
        raise ConfigurationError(f"Missing required field '{key}' in configuration")
    return mapping[key]


def _as_float(value: object, field_name: str) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ConfigurationError(f"Field '{field_name}' must be a number")


def _as_positive_float(value: object, field_name: str) -> float:
    number = _as_float(value, field_name)
    _require(number >= 0, f"Field '{field_name}' must be non-negative")
    return number


def _as_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"Field '{field_name}' must be a string")
    return value


@dataclass
class TimeProfileConfig:
    start_minute: int
    end_minute: int
    multiplier: float

    @staticmethod
    def from_mapping(mapping: Mapping[str, object]) -> "TimeProfileConfig":
        try:
            start = int(mapping.get("start", 0))
            end = int(mapping.get("end", 24 * 60))
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ConfigurationError("Time profile start/end must be integers") from exc
        multiplier = _as_positive_float(mapping.get("multiplier", 1.0), "multiplier")
        _require(start != end, "Time profile start and end cannot be identical")
        _require(multiplier >= 0, "Time profile multiplier must be non-negative")
        return TimeProfileConfig(start, end, multiplier)


@dataclass
class NodeConfig:
    id: str
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    metadata: MutableMapping[str, object] = field(default_factory=dict)

    @staticmethod
    def from_mapping(mapping: Mapping[str, object]) -> "NodeConfig":
        node_id = _as_string(_get(mapping, "id"), "id")
        name_obj = mapping.get("name")
        name = _as_string(name_obj, "name") if isinstance(name_obj, str) else None
        latitude = None
        longitude = None
        if mapping.get("latitude") is not None:
            latitude = _as_float(mapping["latitude"], "latitude")
        if mapping.get("longitude") is not None:
            longitude = _as_float(mapping["longitude"], "longitude")
        metadata = {
            key: value
            for key, value in mapping.items()
            if key not in {"id", "name", "latitude", "longitude"}
        }
        return NodeConfig(node_id, name, latitude, longitude, metadata)


@dataclass
class EdgeConfig:
    source: str
    target: str
    length_km: float
    base_travel_time_hours: float
    fuel_cost_per_km: float
    loss_probability: float
    risk_factor: float
    time_profiles: Sequence[TimeProfileConfig]
    fuel_profiles: Sequence[TimeProfileConfig]
    loss_profiles: Sequence[TimeProfileConfig]
    risk_profiles: Sequence[TimeProfileConfig]
    restrictions: Mapping[str, object]

    @staticmethod
    def from_mapping(mapping: Mapping[str, object]) -> "EdgeConfig":
        source = _as_string(_get(mapping, "source"), "source")
        target = _as_string(_get(mapping, "target"), "target")
        length = _as_positive_float(mapping.get("length_km", 0.0), "length_km")
        base_travel_time = _as_positive_float(
            mapping.get("base_travel_time_hours", 1.0), "base_travel_time_hours"
        )
        _require(base_travel_time > 0, "base_travel_time_hours must be greater than zero")
        fuel_cost_per_km = _as_positive_float(mapping.get("fuel_cost_per_km", 1.0), "fuel_cost_per_km")
        loss_probability = _as_positive_float(mapping.get("loss_probability", 0.0), "loss_probability")
        risk_factor = _as_positive_float(mapping.get("risk_factor", 0.0), "risk_factor")

        profiles = {
            "time_profiles": tuple(
                TimeProfileConfig.from_mapping(item)
                for item in _iter_mappings(mapping.get("time_profiles", []), "time_profiles")
            ),
            "fuel_profiles": tuple(
                TimeProfileConfig.from_mapping(item)
                for item in _iter_mappings(mapping.get("fuel_profiles", []), "fuel_profiles")
            ),
            "loss_profiles": tuple(
                TimeProfileConfig.from_mapping(item)
                for item in _iter_mappings(mapping.get("loss_profiles", []), "loss_profiles")
            ),
            "risk_profiles": tuple(
                TimeProfileConfig.from_mapping(item)
                for item in _iter_mappings(mapping.get("risk_profiles", []), "risk_profiles")
            ),
        }

        restrictions = {
            key: value
            for key, value in mapping.items()
            if key
            not in {
                "source",
                "target",
                "length_km",
                "base_travel_time_hours",
                "fuel_cost_per_km",
                "loss_probability",
                "risk_factor",
                "time_profiles",
                "fuel_profiles",
                "loss_profiles",
                "risk_profiles",
            }
        }

        return EdgeConfig(
            source,
            target,
            length,
            base_travel_time,
            fuel_cost_per_km,
            loss_probability,
            risk_factor,
            profiles["time_profiles"],
            profiles["fuel_profiles"],
            profiles["loss_profiles"],
            profiles["risk_profiles"],
            restrictions,
        )


def _iter_mappings(value: object, field_name: str) -> Iterable[Mapping[str, object]]:
    if value is None:
        return ()
    if not isinstance(value, Iterable):
        raise ConfigurationError(f"Field '{field_name}' must be a sequence of mappings")
    result: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ConfigurationError(f"Elements of '{field_name}' must be mappings")
        result.append(item)
    return tuple(result)


@dataclass
class ScenarioConfig:
    nodes: Sequence[NodeConfig]
    edges: Sequence[EdgeConfig]
    parameters: Mapping[str, object]

    @staticmethod
    def from_mapping(mapping: Mapping[str, object]) -> "ScenarioConfig":
        nodes = tuple(
            NodeConfig.from_mapping(node)
            for node in _iter_mappings(mapping.get("nodes", []), "nodes")
        )
        _require(nodes, "Configuration must contain at least one node")
        edges = tuple(
            EdgeConfig.from_mapping(edge)
            for edge in _iter_mappings(mapping.get("edges", []), "edges")
        )
        _require(edges, "Configuration must contain at least one edge")

        node_ids = {node.id for node in nodes}
        for edge in edges:
            _require(edge.source in node_ids, f"Edge source '{edge.source}' is not defined as a node")
            _require(edge.target in node_ids, f"Edge target '{edge.target}' is not defined as a node")

        parameters = mapping.get("parameters", {})
        if not isinstance(parameters, Mapping):
            raise ConfigurationError("Parameters section must be a mapping")

        return ScenarioConfig(nodes=nodes, edges=edges, parameters=parameters)


__all__ = [
    "ScenarioConfig",
    "NodeConfig",
    "EdgeConfig",
    "TimeProfileConfig",
    "ConfigurationError",
]
