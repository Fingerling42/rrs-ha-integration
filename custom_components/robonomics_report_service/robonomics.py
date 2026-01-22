import asyncio
import logging
import time
import json
from typing import Callable
from collections import deque

from homeassistant.core import HomeAssistant
from robonomicsinterface import Account, Datalog
from substrateinterface import Keypair, KeypairType
from substrateinterface.exceptions import (
    SubstrateRequestException,
    ExtrinsicFailedException
)
from tenacity import Retrying, stop_after_attempt, wait_fixed

from .const import ROBONOMICS_WSS

from .ipfs import IPFS

_LOGGER = logging.getLogger(__name__)


class Robonomics:
    """Main class to handle Robonomics functionality"""

    def __init__(
        self,
        hass: HomeAssistant,
        sender_seed: str,
    ):
        self.hass: HomeAssistant = hass
        self.sender_seed: str = sender_seed
        self.current_wss: str = ROBONOMICS_WSS[0]
        self.sender_account: Account = Account(
            self.sender_seed,
            crypto_type=KeypairType.ED25519,
            remote_ws=self.current_wss,
        )
        self.sender_address: str = self.sender_account.get_address()
        _LOGGER.debug("Sender address: %s", self.sender_address)

        self._datalog_queue = deque()
        self._datalogs_are_sending = False
        self._worker_task: asyncio.Task | None = None
        self._queue_lock = asyncio.Lock()

    @staticmethod
    def generate_seed() -> str:
        """Return mnemonic phrase as seed for account"""
        seed = Keypair.generate_mnemonic()
        return seed

    async def send_datalog(self, data_to_send: str | dict) -> None:
        """Send datalog, async style"""
        if isinstance(data_to_send, dict):
            data_to_send = json.dumps(data_to_send)
        await self._handle_datalog_request(data_to_send)

    @staticmethod
    def _retry_decorator(func: Callable):
        def wrapper(self, *args, **kwargs):
            for attempt in Retrying(
                wait=wait_fixed(2), stop=stop_after_attempt(len(ROBONOMICS_WSS))
            ):
                with attempt:
                    try:
                        res = func(self, *args, **kwargs)
                        return res
                    except TimeoutError:
                        self.change_current_wss()
                        raise
                    except ExtrinsicFailedException as e:
                        _LOGGER.warning("Datalog failed exception: %s", e)
                        return False
                    except SubstrateRequestException as e:
                        code = None

                        if e.args:
                            first = e.args[0]
                            if isinstance(first, dict):
                                code = first.get("code")

                        if code == 1014:
                            _LOGGER.warning(
                                "Datalog sending exception: %s, retrying...",
                                e
                            )
                            time.sleep(8)
                            raise

                        _LOGGER.warning("Datalog sending exception: %s", e)
                        return False

                    except Exception as e:
                        _LOGGER.warning("Datalog sending exeption: %s", e)
                        return False

        return wrapper

    async def _handle_datalog_request(self, data_to_send: str) -> None:
        self._datalog_queue.append(data_to_send)
        _LOGGER.debug(
            "New datalog request, queue length: %d",
            len(self._datalog_queue)
        )
        async with self._queue_lock:
            if self._worker_task is None or self._worker_task.done():
                self._worker_task = self.hass.async_create_task(
                    self._datalog_worker()
                )

    async def _datalog_worker(self) -> None:
        self._datalogs_are_sending = True
        try:
            while self._datalog_queue:
                data_to_send = self._datalog_queue.popleft()

                try:
                    res = await asyncio.to_thread(
                        self._send_datalog,
                        data_to_send
                    )
                except Exception:
                    _LOGGER.exception("Datalog send crashed")
                    res = False

                if not res:
                    try:
                        await IPFS(self.hass).unpin_from_pinata(data_to_send)
                    except Exception:
                        _LOGGER.exception(
                            "Failed to unpin from Pinata after datalog failure"
                        )
        finally:
            self._datalogs_are_sending = False
            # In case the worker reached the end of the queue,
            # but did not have time to set worker_task = None,
            # and at the same time a new request for the datalog appeared.
            async with self._queue_lock:
                self._worker_task = None
                if self._datalog_queue:
                    self._worker_task = self.hass.async_create_task(
                        self._datalog_worker()
                    )

    @_retry_decorator
    def _send_datalog(self, data_to_send: str) -> bool:
        _LOGGER.debug("Start creating datalog with data: %s", data_to_send)
        datalog = Datalog(
            self.sender_account, rws_sub_owner=self.sender_address
        )
        receipt = datalog.record(data_to_send)
        _LOGGER.debug(
            "Datalog created with hash: %s, %d datalogs left in the queue",
            receipt,
            len(self._datalog_queue)
        )
        return True

    def change_current_wss(self) -> None:
        """Set next current wss"""

        current_index = ROBONOMICS_WSS.index(self.current_wss)
        if current_index == (len(ROBONOMICS_WSS) - 1):
            next_index = 0
        else:
            next_index = current_index + 1
        self.current_wss = ROBONOMICS_WSS[next_index]
        _LOGGER.debug("New Robonomics ws is %s", self.current_wss)
        self.sender_account: Account = Account(
            seed=self.sender_seed,
            crypto_type=KeypairType.ED25519,
            remote_ws=self.current_wss,
        )
