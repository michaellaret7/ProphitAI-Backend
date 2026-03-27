"""Custom exceptions for the API layer."""


class BrokerNotConnectedError(Exception):
    """Raised when a controller requires a broker connection but the user has none."""

    pass
