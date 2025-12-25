import logging
import os
from typing import List

from homeassistant.core import HomeAssistant

from .const import (
    LOG_FILE_NAME,
    TRACES_FILE_NAME,
    IPFS_PROBLEM_REPORT_FOLDER,
    PROBLEM_SERVICE_ROBONOMICS_ADDRESS,
)

from .ipfs import IPFS, PinataKeysRewoked
from .utils.file_handler import (
    create_temp_dir_with_encrypted_files,
    delete_temp_dir,
    get_tempdir_filenames
)
from .robonomics import Robonomics

_LOGGER = logging.getLogger(__name__)


class ReportService:
    """Main class to pass HA logs to Robonomics parachain"""

    def __init__(self, hass: HomeAssistant, robonomics: Robonomics):
        self.hass = hass
        self.robonomics = robonomics
        self.ipfs = IPFS(hass)

    async def async_init(self) -> None:
        """Initial routine in async style"""

        await self._clear_temp_dirs()

    async def send_report(self) -> None:
        """Send report with logs as datalog"""

        _LOGGER.debug("Sending a new report is started")

        try:
            temp_dir = await self._get_temp_dir_with_encrypted_logs()

            data_to_send = await self.ipfs.pin_to_pinata(temp_dir)

            if data_to_send is not None:
                await self.robonomics.send_datalog(data_to_send)

        except PinataKeysRewoked as e:
            _LOGGER.error("Exception in creating files to send: %s", e)

        finally:
            await self._remove_temp_dir(temp_dir)

        _LOGGER.debug("A new report is sent")

    async def _get_temp_dir_with_encrypted_logs(self) -> str:
        files = self._get_logs_files()

        temp_dir = await self._async_create_temp_dir_with_encrypted_files(files)

        return temp_dir

    def _get_logs_files(self) -> List[str]:
        hass_config_path = self.hass.config.path()
        files = []

        if os.path.isfile(f"{hass_config_path}/{LOG_FILE_NAME}"):
            files.append(f"{hass_config_path}/{LOG_FILE_NAME}")
        if os.path.isfile(f"{hass_config_path}/{TRACES_FILE_NAME}"):
            files.append(f"{hass_config_path}/{TRACES_FILE_NAME}")

        return files

    async def _async_create_temp_dir_with_encrypted_files(
            self,
            files: List[str]
            ) -> str:
        return await self.hass.async_add_executor_job(
            self._create_temp_dir_with_encrypted_files, files
        )

    def _create_temp_dir_with_encrypted_files(self, files: List[str]) -> str:
        return create_temp_dir_with_encrypted_files(
            IPFS_PROBLEM_REPORT_FOLDER,
            files,
            self.robonomics.sender_seed,
            PROBLEM_SERVICE_ROBONOMICS_ADDRESS,
        )

    async def _clear_temp_dirs(self) -> None:
        dirs_to_delete = await self.hass.async_add_executor_job(
            get_tempdir_filenames, IPFS_PROBLEM_REPORT_FOLDER
        )
        for dirname in dirs_to_delete:
            await self._remove_temp_dir(dirname)

    async def _remove_temp_dir(self, temp_dir: str) -> None:
        if os.path.exists(temp_dir):
            await self.hass.async_add_executor_job(delete_temp_dir, temp_dir)
            _LOGGER.debug("Temp directory %s was deleted", temp_dir)
