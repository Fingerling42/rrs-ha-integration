import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

VERSION_STORAGE = 6

async def async_save_to_store(
        hass: HomeAssistant,
        key: str,
        data: dict[str, Any]
        ) -> None:
    """
    Generate dynamic data to store and save it to the filesystem.

    The data is only written if the content on the disk has changed
    by reading the existing content and comparing it.

    If the data has changed this will generate two executor jobs

    If the data has not changed this will generate one executor job
    """
    current = await async_load_from_store(hass, key)
    if current is None or current != data:
        await _get_store_for_key(hass, key).async_save(data)
        return
    _LOGGER.debug("Content in .storage/%s was't changed", _get_store_key(key))


async def async_load_from_store(
        hass: HomeAssistant,
        key: str
        ) -> dict[str, Any]:
    """Load the retained data from store and return de-serialized data."""
    return await _get_store_for_key(hass, key).async_load() or {}


async def async_remove_store(hass: HomeAssistant, key: str) -> None:
    """Remove data from store for given key"""
    await _get_store_for_key(hass, key).async_remove()


def _get_store_for_key(hass: HomeAssistant, key: str) -> Store[Any]:
    """Create a Store object for the key."""
    return Store(
        hass,
        VERSION_STORAGE,
        _get_store_key(key),
        encoder=JSONEncoder,
        atomic_writes=True,
    )

def _get_store_key(key: str) -> str:
    """Return the key to use with homeassistant.helpers.storage.Storage."""
    return f"robonomics_report_service.{key}"
