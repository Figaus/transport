"""Custom exception hierarchy for the supply chain optimizer."""


class SupplyChainError(Exception):
    """Base class for supply chain related errors."""


class ConfigurationError(SupplyChainError):
    """Raised when a scenario configuration fails validation."""


class RoutingError(SupplyChainError):
    """Raised when the routing algorithm fails to find a valid path."""


__all__ = ["SupplyChainError", "ConfigurationError", "RoutingError"]
