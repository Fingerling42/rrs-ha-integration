import logging

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CREDS_STORAGE_KEY,
    CONF_SENDER_SEED,
    PROBLEM_SERVICE_ROBONOMICS_ADDRESS,
    OWNER_ADDRESS,
    ERROR_WATCHERS_MANAGER,
    PROBLEM_REPORT_SERVICE
)

from .robonomics import Robonomics
from .error_watchers.error_watchers_manager import ErrorWatchersManager
from .report_service import ReportService
from .utils.ha_storage import async_remove_store, async_load_from_store

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Setup of a specific integration instance.

    Called by the config entries manager if:
    - the user added the integration via the UI
    - HA restores existing entries upon startup
    """

    # Check that the global dict for integration exists
    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    # Load credentials from storage
    creds_storage = await async_load_from_store(hass, CREDS_STORAGE_KEY)

    # Prepare Robonomics class
    robonomics = Robonomics(
        hass,
        creds_storage[CONF_SENDER_SEED],
        creds_storage.get(OWNER_ADDRESS)
    )

    # Prepare report service
    report_service = ReportService(
        hass,
        robonomics,
        creds_storage[PROBLEM_SERVICE_ROBONOMICS_ADDRESS]
    )
    await report_service.async_init()

    # Register send_report as HA service
    hass.data[DOMAIN][entry.entry_id]["report_service"] = report_service

    async def _handle_send_report(call: ServiceCall) -> None:
        # Allow calling the service from UI, just to send pure logs
        if not call.data:
            await report_service.send_report(issue=None)
            return

        issue = dict(call.data)
        await report_service.send_report(issue=issue)

    hass.services.async_register(
        DOMAIN,
        PROBLEM_REPORT_SERVICE,
        _handle_send_report
    )

    # Configure and start manager for errors watchers
    error_watchers_manager = ErrorWatchersManager(hass)
    error_watchers_manager.setup_watchers()
    hass.data[DOMAIN][ERROR_WATCHERS_MANAGER] = error_watchers_manager

    return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """
    Global integration setup.

    Called at HA startup when it loads the configuration.
    """
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a config entry.

    It calls during integration's removing.
    """
    hass.data[DOMAIN][ERROR_WATCHERS_MANAGER].remove_watchers()

    hass.services.async_remove(DOMAIN, PROBLEM_REPORT_SERVICE)

    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    await async_remove_store(hass, CREDS_STORAGE_KEY)
    _LOGGER.debug("Credentials deleted from storage")

    return True
