import logging
import os
import asyncio
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    LOG_FILE_NAME,
    TRACES_FILE_NAME,
    RRS_REPORT_TEMP_DIR,
)

from .ipfs import IPFS, PinataKeysRewoked
from .utils.file_handler import (
    create_temp_dir_with_encrypted_files,
    delete_temp_dir,
    get_temp_dirs,
    create_temp_archive,
    create_temp_dir_with_issue
)
from .robonomics import Robonomics

_LOGGER = logging.getLogger(__name__)


class ReportService:
    """Main class to pass HA logs to Robonomics parachain"""

    def __init__(self,
        hass: HomeAssistant,
        robonomics: Robonomics,
        problem_service_address: str,
    ):
        self.hass = hass
        self.robonomics = robonomics
        self.problem_service_address = problem_service_address
        self.ipfs = IPFS(hass)
        self._send_lock = asyncio.Lock()

    async def async_init(self) -> None:
        """Initial routine in async style"""

        await self._clear_temp_dirs()

    async def send_report(self, issue: dict[str, Any] | None = None) -> None:
        """Send report with issue/logs as datalog"""

        _LOGGER.debug("Sending a new report is started")

        temp_logs_dir: str | None = None
        temp_archive_dir: str | None = None
        temp_issue_dir: str | None = None

        async with self._send_lock:
            try:
                temp_logs_dir, temp_issue_dir = (
                    await self._get_temp_dir_with_encrypted_payload(issue)
                )

                temp_archive_path = await self._async_create_temp_archive(
                    temp_logs_dir,
                )
                temp_archive_dir = os.path.dirname(temp_archive_path)

                data_to_send = await self.ipfs.pin_file_to_pinata(
                    temp_archive_path
                )

                if data_to_send is not None:
                    await self.robonomics.send_datalog(data_to_send)
                    _LOGGER.debug("A new report is added to datalog queue")
                else:
                    _LOGGER.warning("Pinata returned no data; report not sent")

            except PinataKeysRewoked as e:
                _LOGGER.error("Failed to pin report to Pinata: %s", e)

            except ValueError as e:
                _LOGGER.warning("Report not sent: %s", e)

            except Exception:
                _LOGGER.exception("Unexpected error while sending report")

            finally:
                await self._delete_temp_dir(temp_logs_dir)
                await self._delete_temp_dir(temp_archive_dir)
                await self._delete_temp_dir(temp_issue_dir)

    async def _get_temp_dir_with_encrypted_payload(
            self, issue: dict[str, Any] | None
        ) -> tuple[str, str | None]:

        files = self._get_logs_files()

        temp_issue_dir: str | None = None

        if issue is not None:
            issue_path = (
                await self._async_create_temp_dir_with_issue(issue)
            )
            files.append(issue_path)
            temp_issue_dir = os.path.dirname(issue_path)

        if not files:
            raise ValueError("No files found to include in report")

        temp_logs_dir = (
            await self._async_create_temp_dir_with_encrypted_files(files)
        )

        return temp_logs_dir, temp_issue_dir

    def _get_logs_files(self) -> list[str]:
        hass_config_path = self.hass.config.path()
        files = []

        log_path = os.path.join(hass_config_path, LOG_FILE_NAME)
        traces_path = os.path.join(hass_config_path, TRACES_FILE_NAME)

        if os.path.isfile(log_path):
            files.append(log_path)
        if os.path.isfile(traces_path):
            files.append(traces_path)

        return files

    async def _async_create_temp_dir_with_encrypted_files(
        self,
        files: list[str]
    ) -> str:
        return await self.hass.async_add_executor_job(
            self._create_temp_dir_with_encrypted_files, files
        )

    def _create_temp_dir_with_encrypted_files(self, files: list[str]) -> str:
        return create_temp_dir_with_encrypted_files(
            RRS_REPORT_TEMP_DIR,
            files,
            self.robonomics.sender_account,
            [self.problem_service_address],
        )

    async def _clear_temp_dirs(self) -> None:
        dirs_to_delete = await self.hass.async_add_executor_job(
            get_temp_dirs, RRS_REPORT_TEMP_DIR
        )
        for dir_name in dirs_to_delete:
            await self._delete_temp_dir(dir_name)

    async def _delete_temp_dir(self, temp_dir: str | None) -> None:
        if not temp_dir:
            return
        if os.path.exists(temp_dir):
            await self.hass.async_add_executor_job(delete_temp_dir, temp_dir)

    async def _async_create_temp_archive(
        self,
        dir_to_archive: str,
    ) -> str:
        return await self.hass.async_add_executor_job(
            self._create_temp_archive, dir_to_archive
        )

    def _create_temp_archive(self, dir_to_archive: str) -> str:
        return create_temp_archive(
            dir_to_archive,
            self.robonomics.sender_address,
            RRS_REPORT_TEMP_DIR
        )

    async def _async_create_temp_dir_with_issue(
        self,
        issue: dict[str, Any]
    ) -> str:
        return await self.hass.async_add_executor_job(
            self._create_temp_dir_with_issue, issue
        )

    def _create_temp_dir_with_issue(self, issue: dict[str, Any]) -> str:
        return create_temp_dir_with_issue(
            issue,
            RRS_REPORT_TEMP_DIR
        )
