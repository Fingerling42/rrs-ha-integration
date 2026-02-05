import abc
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from ...const import (
    DOMAIN,
    PROBLEM_REPORT_SERVICE,
    CREDS_STORAGE_KEY,
    CONF_SENDER_EMAIL
)

from ...utils.ha_storage import async_load_from_store

_LOGGER = logging.getLogger(__name__)


class ErrorWatcher(abc.ABC):
    """Base class for error watchers"""
    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    @abc.abstractmethod
    def setup(self):
        """Draft to start watcher"""

    @abc.abstractmethod
    def remove(self):
        """Draft to stop watcher"""

    async def _get_email(self) -> str | None:
        creds_storage = await async_load_from_store(
            self.hass, CREDS_STORAGE_KEY)
        email = creds_storage.get(CONF_SENDER_EMAIL)
        return email

    async def _send_report(self, issue: dict[str, Any]):
        """Call send_report HA service (fire-and-forget but error-aware)."""

        async def _call() -> None:
            try:
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        DOMAIN,
                        PROBLEM_REPORT_SERVICE,
                        service_data=issue,
                        blocking=True
                    )
                )
            except (ServiceValidationError, HomeAssistantError) as e:
                _LOGGER.warning("Problem report service failed: %s", e)

            except Exception:
                _LOGGER.exception(
                    "Unexpected error while calling problem report service"
                )

        self.hass.async_create_task(_call())
