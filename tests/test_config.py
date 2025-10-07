import pytest

from supply_chain.config import ConfigurationError, ScenarioConfig


def test_missing_nodes_raises_configuration_error():
    data = {
        "nodes": [],
        "edges": [
            {
                "source": "a",
                "target": "b",
                "length_km": 1,
                "base_travel_time_hours": 1,
            }
        ],
    }

    with pytest.raises(ConfigurationError):
        ScenarioConfig.from_mapping(data)


def test_unknown_edge_node_raises_configuration_error():
    data = {
        "nodes": [{"id": "a"}],
        "edges": [
            {
                "source": "a",
                "target": "b",
                "length_km": 10,
                "base_travel_time_hours": 2,
            }
        ],
    }

    with pytest.raises(ConfigurationError):
        ScenarioConfig.from_mapping(data)


def test_high_risk_requires_explicit_opt_in():
    data = {
        "nodes": [{"id": "a"}, {"id": "b"}],
        "edges": [
            {
                "source": "a",
                "target": "b",
                "length_km": 10,
                "base_travel_time_hours": 1,
                "risk_factor": 1.5,
            }
        ],
    }

    scenario = ScenarioConfig.from_mapping(data)

    from supply_chain.graph import build_graph_from_scenario

    with pytest.raises(ConfigurationError):
        build_graph_from_scenario(scenario)
