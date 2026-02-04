from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ..exceptions import StorageError


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
    try:
        current = await async_load_from_store(hass, key)
        if current != data:
            await _get_store_for_key(hass, key).async_save(data)
    except Exception as e:
        raise StorageError(
            f"Failed to save store key: {_get_store_key(key)}"
        ) from e


async def async_load_from_store(
        hass: HomeAssistant,
        key: str
        ) -> dict[str, Any]:
    """Load the retained data from store and return de-serialized data."""
    try:
        return await _get_store_for_key(hass, key).async_load() or {}
    except Exception as e:
        raise StorageError(
            f"Failed to load store key: {_get_store_key(key)}"
        ) from e


async def async_remove_store(hass: HomeAssistant, key: str) -> None:
    """Remove data from store for given key"""
    try:
        await _get_store_for_key(hass, key).async_remove()
    except Exception as e:
        raise StorageError(
            f"Failed to remove store key: {_get_store_key(key)}"
        ) from e


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
