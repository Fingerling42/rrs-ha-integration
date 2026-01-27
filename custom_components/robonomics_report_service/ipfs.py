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

    async def pin_files_from_dir_to_pinata(
            self, dir_name: str
        ) -> tp.Optional[IpfsHashes]:
        """
        Upload and pin files from directory to Pinata and get their IPFS hashes
        """
        pinata = await self._get_pinata_with_creds()

        if pinata is None:
            return None

        return await self.hass.async_add_executor_job(
            self._pin_files_from_dir_to_pinata,
            dir_name,
            pinata
        )

    async def pin_file_to_pinata(self, file_path: str) -> tp.Optional[str]:
        """Upload and pin one file to Pinata and get its hash"""
        pinata = await self._get_pinata_with_creds()

        if pinata is None:
            return None

        return await self.hass.async_add_executor_job(
            self._pin_file_to_pinata,
            file_path,
            pinata
        )

    async def unpin_files_from_pinata(
        self,
        payload: str | IpfsHashes
    ) -> None:
        """Unpin IPFS file from Pinata"""

        pinata = await self._get_pinata_with_creds()

        if pinata is None:
            return

        ipfs_hashes: IpfsHashes | None = None

        # If IPFS hashes provided in dict
        if isinstance(payload, dict):
            ipfs_hashes = payload

        # If IPFS hashes provided in str
        else:
            s = payload.strip()

            # If str with hashes is JSON string
            if s.startswith("{"):
                try:
                    loaded = json.loads(s)
                except json.JSONDecodeError:
                    _LOGGER.warning("Unexpected unpin payload: invalid JSON")
                    return

                if not isinstance(loaded, dict):
                    _LOGGER.warning(
                        "Unexpected unpin payload type: %s", type(loaded)
                    )
                    return

                ipfs_hashes = tp.cast(IpfsHashes, loaded)

            # If str is just one hash
            else:
                ipfs_hashes = {"archive": s}

        await self.hass.async_add_executor_job(
            self._unpin_files_from_pinata,
            ipfs_hashes,
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

    def _pin_files_from_dir_to_pinata(
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

    def _pin_file_to_pinata(
        self,
        file_path: str,
        pinata: PinataPy
    ) -> tp.Optional[str]:

        if not os.path.isfile(file_path):
            _LOGGER.error(
                "File for uploading to Pinata not found: %s", file_path
            )
            return None

        try:
            res = pinata.pin_file_to_ipfs(
                file_path,
                save_absolute_paths=False
            )
        except Exception as e:
            _LOGGER.error(
                "Pinata pin_file_to_ipfs failed for %s: %s",
                file_path,
                e
            )
            return None

        if not isinstance(res, dict):
            _LOGGER.error("Can't pin to Pinata, unexpected response: %s", res)
            return None

        ipfs_hash = res.get("IpfsHash")

        if isinstance(ipfs_hash, str) and ipfs_hash:
            _LOGGER.debug(
                "Added file %s to Pinata. Hash is: %s",
                file_path,
                ipfs_hash
            )
            return ipfs_hash

        status = res.get("status")
        text = res.get("text", "")

        if (
            status == 403 and isinstance(text, str)
            and "API_KEY_REVOKED" in text
            ):
            _LOGGER.warning("Pinata keys were revoked")
            raise PinataKeysRewoked()

        _LOGGER.error("Can't pin to pinata with responce: %s", res)
        return None

    def _unpin_files_from_pinata(
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
