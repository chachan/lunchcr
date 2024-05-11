"""Utilities module"""
import logging
import os

logging.getLogger("lunchable.models._core").disabled = True

def _str(x):
    return x.strip() if x else ""

def _float(x):
    return float(x.strip())


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
