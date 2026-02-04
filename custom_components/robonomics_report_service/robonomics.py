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
from .exceptions import RobonomicsError

_LOGGER = logging.getLogger(__name__)


class Robonomics:
    """Main class to handle Robonomics functionality"""

    def __init__(
        self,
        hass: HomeAssistant,
        ipfs: IPFS,
        sender_seed: str,
        owner_address: str | None = None,
    ):
        self.hass: HomeAssistant = hass
        self.ipfs: IPFS = ipfs
        self.sender_seed: str = sender_seed
        self.current_wss: str = ROBONOMICS_WSS[0]
        self.sender_account: Account = Account(
            self.sender_seed,
            crypto_type=KeypairType.ED25519,
            remote_ws=self.current_wss,
        )
        self.sender_address: str = self.sender_account.get_address()

        self._owner_address = owner_address

        self._datalog_queue = deque()
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
            last_exc: Exception | None = None
            attempts = len(ROBONOMICS_WSS)

            for attempt in Retrying(
                wait=wait_fixed(2),
                stop=stop_after_attempt(attempts),
                reraise=False,
            ):
                with attempt:
                    try:
                        return func(self, *args, **kwargs)

                    except TimeoutError as e:
                        last_exc = e
                        self.change_current_wss()
                        raise

                    except SubstrateRequestException as e:
                        last_exc = e
                        code = self._substrate_code(e)

                        if code == 1014:
                            time.sleep(8)
                            self.change_current_wss()
                            raise

                        self.change_current_wss()
                        raise

                    except ExtrinsicFailedException as e:
                        last_exc = e
                        break

                    except Exception as e:
                        last_exc = e
                        self.change_current_wss()
                        raise

            if last_exc is None:
                raise RobonomicsError("Failed to send datalog")

            code = self._substrate_code(last_exc)
            reason = self._exc_short(last_exc)

            msg = f"Failed to send datalog ({reason})"
            if code:
                msg = f"Failed to send datalog (code={code}, {reason})"

            raise RobonomicsError(msg) from last_exc

        return wrapper

    async def _handle_datalog_request(self, data_to_send: str) -> None:
        self._datalog_queue.append(data_to_send)
        async with self._queue_lock:
            if self._worker_task is None or self._worker_task.done():
                self._worker_task = self.hass.async_create_task(
                    self._datalog_worker()
                )

    async def _datalog_worker(self) -> None:
        try:
            while self._datalog_queue:
                data_to_send = self._datalog_queue.popleft()

                try:
                    await asyncio.to_thread(
                        self._send_datalog,
                        data_to_send
                    )
                except RobonomicsError as e:
                    _LOGGER.warning(
                        "Datalog send failed "
                        "(will drop payload from queue): %s",
                        e
                    )
                    try:
                        result = await self.ipfs.unpin_files_from_pinata(
                            data_to_send
                        )
                    except Exception:
                        result = None

                    if result and result.failed:
                        _LOGGER.warning(
                            "Pinata cleanup incomplete after datalog " \
                            "failure (removed=%s/%s, failed=%s)",
                            result.succeeded, result.attempted, result.failed
                        )


        finally:
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
        # If no owner address is provided, use RWS of sender
        datalog = Datalog(
            self.sender_account,
            rws_sub_owner=self._owner_address or self.sender_address
        )

        datalog.record(data_to_send)

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

    @staticmethod
    def _exc_short(e: BaseException) -> str:
        name = e.__class__.__name__
        msg = str(e).strip()
        return f"{name}: {msg}" if msg else name

    @staticmethod
    def _substrate_code(e: BaseException) -> str | None:
        if (
            isinstance(e, SubstrateRequestException)
            and e.args
            and isinstance(e.args[0], dict)
        ):
            code = e.args[0].get("code")
            return str(code) if code is not None else None
        return None
