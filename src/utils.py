"""Utilities module"""
import logging
import os

_str = lambda x: x.strip() if x else ""
_float = lambda x: float(x.strip())


def config_logger(
    name="",
    level=logging.DEBUG if os.environ.get("DEBUG", "False").capitalize() == "True" else logging.INFO,
    _format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    handler=logging.StreamHandler,
    propagate=True,
):
    """configures a logger"""
    _handler = handler()
    _handler.setFormatter(logging.Formatter(_format))
    _logger = logging.getLogger(name)
    _logger.addHandler(_handler)
    _logger.setLevel(level)
    _logger.propagate = propagate
    return _logger
