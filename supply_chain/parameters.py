"""Data classes describing routing parameters and weights."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class CostWeights:
    """Weights for individual cost components used in optimization."""

    fuel: float = 1.0
    time: float = 1.0
    loss: float = 1.0
    risk: float = 1.0

    @classmethod
    def from_mapping(cls, data: Mapping[str, float]) -> "CostWeights":
        return cls(
            fuel=float(data.get("fuel", 1.0)),
            time=float(data.get("time", 1.0)),
            loss=float(data.get("loss", 1.0)),
            risk=float(data.get("risk", 1.0)),
        )

    def as_dict(self) -> dict[str, float]:
        return {"fuel": self.fuel, "time": self.time, "loss": self.loss, "risk": self.risk}


@dataclass(frozen=True)
class RoutingParameters:
    """Global parameters configuring the routing optimization."""

    weights: CostWeights
    time_value_per_hour: float = 100.0
    loss_penalty: float = 2000.0
    risk_penalty: float = 1000.0
    default_speed_kmph: float = 60.0

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "RoutingParameters":
        weights_data = data.get("weights", {}) if isinstance(data, Mapping) else {}
        weights = CostWeights.from_mapping(weights_data) if isinstance(weights_data, Mapping) else CostWeights()
        return cls(
            weights=weights,
            time_value_per_hour=float(data.get("time_value_per_hour", 100.0)),
            loss_penalty=float(data.get("loss_penalty", 2000.0)),
            risk_penalty=float(data.get("risk_penalty", 1000.0)),
            default_speed_kmph=float(data.get("default_speed_kmph", 60.0)),
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "weights": self.weights.as_dict(),
            "time_value_per_hour": self.time_value_per_hour,
            "loss_penalty": self.loss_penalty,
            "risk_penalty": self.risk_penalty,
            "default_speed_kmph": self.default_speed_kmph,
        }
