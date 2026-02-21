"""Utilities module."""

import logging
import os
import re
import unicodedata
from typing import TYPE_CHECKING

from lunchable import LunchMoney

if TYPE_CHECKING:
    from lunchable.models import AssetsObject

logging.getLogger("lunchable.models._core").disabled = True


def _str(x: str) -> str:
    return x.strip() if x else ""


def _float(x: str) -> float:
    return float(x.strip())


def config_logger(name: str = "") -> logging.Logger:
    """Configure a logger."""
    if logging.getLogger(name).hasHandlers():
        return logging.getLogger(name)

    level: int = logging.DEBUG if os.environ.get("DEBUG", "False").capitalize() == "True" else logging.INFO
    _format: str = "%(asctime)s - %(name)s.%(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    handler = logging.StreamHandler

    _handler = handler()
    _handler.setFormatter(logging.Formatter(_format))
    _logger = logging.getLogger(name)
    _logger.addHandler(_handler)
    _logger.setLevel(level)
    _logger.propagate = False
    return _logger


class LunchMoneyCR(LunchMoney):
    """LunchMoney wrapper to include custom logic."""

    def __init__(self, access_token: str) -> None:
        """Initialize."""
        super().__init__(access_token)
        self.cached_assets: list[AssetsObject] = self.get_assets()


def slugify(value: str | float) -> str:
    """Django's slugify."""
    value = str(value)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")
