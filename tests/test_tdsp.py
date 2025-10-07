from pathlib import Path

from supply_chain.app import load_config
from supply_chain.config import ScenarioConfig
from supply_chain.graph import build_graph_from_scenario
from supply_chain.parameters import RoutingParameters
from supply_chain.tdsp import tdsp_a_star


def test_route_follows_expected_path():
    config_path = Path(__file__).resolve().parents[1] / "examples" / "sample_network.json"
    raw_config = load_config(config_path)
    scenario = ScenarioConfig.from_mapping(raw_config)
    graph = build_graph_from_scenario(scenario)
    parameters = RoutingParameters.from_mapping(scenario.parameters)

    result = tdsp_a_star(graph, "mine", "plant", departure_minute=8 * 60, parameters=parameters)
    assert result is not None
    path_nodes = [step.node_id for step in result.path]
    assert path_nodes == ["mine", "hub", "plant"]
    assert result.total_cost > 0
    assert result.total_travel_time_hours > 0
