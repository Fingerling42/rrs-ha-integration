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
    PROBLEM_REPORT_SERVICE,
    CONF_NETWORK
)

from .robonomics import Robonomics
from .ipfs import IPFS
from .error_watchers.error_watchers_manager import ErrorWatchersManager
from .report_service import ReportService
from .utils.ha_storage import async_remove_store, async_load_from_store
from .exceptions import StorageError

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

    try:
        # Load credentials from storage
        creds_storage = await async_load_from_store(hass, CREDS_STORAGE_KEY)

        # Prepare Robonomics and IPFS classes
        ipfs = IPFS(hass)
        robonomics = Robonomics(
            hass,
            creds_storage[CONF_NETWORK],
            ipfs,
            creds_storage[CONF_SENDER_SEED],
            creds_storage.get(OWNER_ADDRESS)
        )

        # Prepare report service
        report_service = ReportService(
            hass,
            ipfs,
            robonomics,
            creds_storage[PROBLEM_SERVICE_ROBONOMICS_ADDRESS]
        )
        await report_service.async_init()
    except (StorageError, KeyError) as e:
        _LOGGER.error(
            "Failed to set up %s: missing/invalid stored credentials: %s",
            DOMAIN, e
        )
        return False

    except Exception:
        _LOGGER.exception("Failed to set up %s due to unexpected error", DOMAIN)
        return False

    # Register send_report as HA service
    hass.data[DOMAIN][entry.entry_id]["report_service"] = report_service

    async def _handle_send_report(call: ServiceCall) -> None:
        # Allow calling the service from UI, just to send pure logs
        issue = dict(call.data) if call.data else None
        await report_service.send_report(issue=issue)

    hass.services.async_register(
        DOMAIN,
        PROBLEM_REPORT_SERVICE,
        _handle_send_report
    )

    # Configure and start manager for errors watchers
    error_watchers_manager = ErrorWatchersManager(hass)
    error_watchers_manager.setup_watchers()
    hass.data[DOMAIN][entry.entry_id][ERROR_WATCHERS_MANAGER] = (
        error_watchers_manager
    )

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
    """
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})

    error_watchers_manager = data.get(ERROR_WATCHERS_MANAGER)

    if error_watchers_manager:
        try:
            error_watchers_manager.remove_watchers()
        except Exception:
            _LOGGER.debug("Failed to remove watchers", exc_info=True)

    hass.services.async_remove(DOMAIN, PROBLEM_REPORT_SERVICE)

    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    return True

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Called when the config entry is removed from Home Assistant."""
    await async_remove_store(hass, CREDS_STORAGE_KEY)
