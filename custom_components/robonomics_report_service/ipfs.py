import logging
import typing as tp
import os
import json

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pinatapy import PinataPy

from .utils.ha_storage import async_load_from_store
from .const import STORAGE_NAME, CONF_PINATA_PUBLIC, CONF_PINATA_SECRET

IpfsHashes = dict[str, str]

_LOGGER = logging.getLogger(__name__)

class PinataKeysRewoked(HomeAssistantError):
    """Pinata API Key has been revoked"""

class IPFS:
    """Class for handling IPFS and Pinata functionality"""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    async def pin_to_pinata(self, dir_name: str) -> tp.Optional[IpfsHashes]:
        """Upload and pin directory to Pinata and get its IPFS hash"""
        pinata = await self._get_pinata_with_creds()

        if pinata is None:
            return None

        return await self.hass.async_add_executor_job(
            self._pin_to_pinata,
            dir_name,
            pinata
        )

    async def unpin_from_pinata(
        self,
        ipfs_hashes: str | IpfsHashes
    ) -> None:
        """Unpin IPFS file from Pinata"""

        pinata = await self._get_pinata_with_creds()

        if pinata is None:
            return

        loaded: object
        if isinstance(ipfs_hashes, str):
            try:
                loaded = json.loads(ipfs_hashes)
            except json.JSONDecodeError:
                _LOGGER.warning("Unexpected unpin payload: invalid JSON")
                return
        else:
            loaded = ipfs_hashes

        if not isinstance(loaded, dict):
            _LOGGER.warning("Unexpected unpin payload type: %s", type(loaded))
            return

        ipfs_hashes_typed = tp.cast(IpfsHashes, loaded)

        await self.hass.async_add_executor_job(
            self._unpin_from_pinata,
            ipfs_hashes_typed,
            pinata
        )

    async def _get_pinata_with_creds(self) -> tp.Optional[PinataPy]:
        storage_data = await async_load_from_store(self.hass, STORAGE_NAME)
        if (
            CONF_PINATA_PUBLIC in storage_data
            and CONF_PINATA_SECRET in storage_data
        ):
            return PinataPy(
                storage_data[CONF_PINATA_PUBLIC],
                storage_data[CONF_PINATA_SECRET]
            )
        return None

    def _pin_to_pinata(
        self,
        dir_name: str,
        pinata: PinataPy
    ) -> tp.Optional[IpfsHashes]:

        dict_with_hashes: IpfsHashes = {}

        try:
            file_names = [
                f for f in os.listdir(dir_name)
                if os.path.isfile(os.path.join(dir_name, f))
            ]
        except OSError as e:
            _LOGGER.error("Can't list dir %s: %s", dir_name, e)
            return None

        for file in file_names:
            path_to_file = os.path.join(dir_name, file)

            try:
                res = pinata.pin_file_to_ipfs(
                    path_to_file,
                    save_absolute_paths=False
                )
            except Exception as e:
                _LOGGER.error(
                    "Pinata pin_file_to_ipfs failed for %s: %s",
                    file,
                    e
                )
                continue

            if not isinstance(res, dict):
                _LOGGER.error(
                    "Can't pin to Pinata, unexpected response: %s",
                    res
                )
                continue


            ipfs_hash = res.get("IpfsHash")

            if isinstance(ipfs_hash, str) and ipfs_hash:
                _LOGGER.debug(
                    "Added file %s to Pinata. Hash is: %s",
                    file,
                    ipfs_hash
                )
                dict_with_hashes[file] = ipfs_hash
                continue

            status = res.get("status")
            text = res.get("text", "")

            if (
                status == 403 and isinstance(text, str)
                and "API_KEY_REVOKED" in text
                ):
                _LOGGER.warning("Pinata keys were revoked")
                raise PinataKeysRewoked()

            _LOGGER.error("Can't pin to pinata with responce: %s", res)

        return dict_with_hashes or None

    def _unpin_from_pinata(
            self,
            ipfs_hashes_dict: IpfsHashes,
            pinata: PinataPy
        ) -> None:
        _LOGGER.debug("Start removing Pinata pins: %s", ipfs_hashes_dict)

        for _, current_hash in ipfs_hashes_dict.items():
            if isinstance(current_hash, str) and current_hash.startswith("Qm"):
                try:
                    res = pinata.remove_pin_from_ipfs(current_hash)
                except Exception as e:
                    _LOGGER.warning("Failed to unpin %s: %s", current_hash, e)
                    continue
                _LOGGER.debug(
                    "Remove response for pin %s: %s",
                    current_hash,
                    res
                )
