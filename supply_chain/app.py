"""Command line interface for the supply chain routing application."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Iterable, Mapping

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except Exception:  # pragma: no cover - no yaml support available
    yaml = None

from .config import ScenarioConfig
from .exceptions import ConfigurationError, RoutingError
from .graph import build_graph_from_scenario
from .parameters import RoutingParameters
from .tdsp import RouteStep, tdsp_a_star


def load_config(path: Path) -> Mapping[str, Any]:
    """Load a scenario configuration from JSON or YAML."""

    data = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is not installed. Please provide a JSON file or install PyYAML.")
        parsed = yaml.safe_load(data)
    else:
        parsed = json.loads(data)

    if not isinstance(parsed, Mapping):
        raise ConfigurationError("Configuration root must be a mapping")
    return parsed


def format_path(path: Iterable[RouteStep]) -> str:
    segments: list[str] = []
    for step in path:
        arrival_hour = step.arrival_minute // 60
        arrival_minute = step.arrival_minute % 60
        segments.append(f"{step.node_id} (arrival {arrival_hour:02d}:{arrival_minute:02d})")
    return " -> ".join(segments)


def _configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Supply chain routing optimizer")
    parser.add_argument("config", type=Path, help="Path to the routing scenario (JSON or YAML)")
    parser.add_argument("--start", required=True, help="Start node identifier")
    parser.add_argument("--goal", required=True, help="Goal node identifier")
    parser.add_argument(
        "--departure",
        type=int,
        default=8 * 60,
        help="Departure time in minutes from start of day (default: 8*60)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for the route summary",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    args = parser.parse_args(argv)

    _configure_logging(args.log_level)

    try:
        raw_config = load_config(args.config)
        scenario = ScenarioConfig.from_mapping(raw_config)
        graph = build_graph_from_scenario(scenario)
        parameters = RoutingParameters.from_mapping(scenario.parameters)
        logging.info(
            "Running optimization start=%s goal=%s departure=%s", args.start, args.goal, args.departure
        )
        result = tdsp_a_star(graph, args.start, args.goal, args.departure, parameters)
        if result is None:
            raise RoutingError("Не удалось построить маршрут с заданными ограничениями")
    except ConfigurationError as exc:
        logging.error("Configuration error: %s", exc)
        print(f"Ошибка конфигурации: {exc}")
        return 2
    except RoutingError as exc:
        logging.warning("Routing failed: %s", exc)
        print(str(exc))
        return 1

    if args.format == "json":
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    else:
        print("Найден оптимальный маршрут:")
        print(format_path(result.path))
        print(f"Суммарные затраты: {result.total_cost:.2f}")
        print(f"Суммарное время в пути: {result.total_travel_time_hours:.2f} ч")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
