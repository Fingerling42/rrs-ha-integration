import abc
from typing import Any

from homeassistant.core import HomeAssistant

from ...const import DOMAIN, PROBLEM_REPORT_SERVICE


class ErrorSource(abc.ABC):
    """Base class for error watchers"""
    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    @abc.abstractmethod
    def setup(self):
        """Draft to start watcher"""

    @abc.abstractmethod
    def remove(self):
        """Draft to stop watcher"""

    async def _send_report(self, issue: dict[str, Any]):
        """Call send_report HA service"""
        self.hass.async_create_task(
            self.hass.services.async_call(
                DOMAIN,
                PROBLEM_REPORT_SERVICE,
                service_data=issue
            )
        )
