import logging
import asyncio
import hashlib
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.components.system_log import DOMAIN as SYSTEM_LOG_DOMAIN
from homeassistant.components.system_log import EVENT_SYSTEM_LOG
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.util.dt as dt_util

from .error_watcher import ErrorWatcher
from ...const import DOMAIN, CHECK_LOGS_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class LoggerHandler(ErrorWatcher):
    """Watcher that react to all warning/errors in logs"""
    def __init__(self, hass: HomeAssistant):
        super().__init__(hass)

        self._event_listener = None

        self._flush_timer_listener = None
        self._period_start = dt_util.utcnow()

        # Buffer for accumulated log records
        self._accumulated_records: dict[str, dict[str, Any]] = {}

        self._lock = asyncio.Lock()

        if SYSTEM_LOG_DOMAIN in self.hass.data:
            self.hass.data[SYSTEM_LOG_DOMAIN].fire_event = True

    @callback
    def setup(self):
        _LOGGER.debug("LoggerHandler initialized")
        # Create listener for event with appearing HA log
        self._event_listener = self.hass.bus.async_listen(
            EVENT_SYSTEM_LOG,
            self._catch_new_log
        )

        # Create timer to flush accumulated log records to send_report service
        self._flush_timer_listener = async_track_time_interval(
            self.hass,
            self._flush,
            timedelta(minutes=CHECK_LOGS_TIMEOUT)
        )

    @callback
    def remove(self):
        if self._event_listener is not None:
            self._event_listener()
            self._event_listener = None

        if self._flush_timer_listener is not None:
            self._flush_timer_listener()
            self._flush_timer_listener = None

        _LOGGER.debug("LoggerHandler removed")

    async def _catch_new_log(self, log_event: Event) -> None:
        """Catch needed logs and add them to the log buffer"""

        log = log_event.data

        # Check only logs that are not related to the report service
        name = log.get("name")
        if isinstance(name, str) and DOMAIN in name:
            return

        # Accept only critical, error and warning levels of logs
        level = log.get("level")
        if level not in ("ERROR", "CRITICAL", "WARNING"):
            return

        # Gather other related fields of log
        source = log.get("source")
        message = log.get("message")

        # Create unique signature of log for deduplication
        # based on name, level and message
        signature_src = f"{name or ''}|{level or ''}|{message or ''}"
        signature = hashlib.sha256(
            signature_src.encode("utf-8", "ignore")
        ).hexdigest()[:16]

        time_now = dt_util.utcnow().isoformat()

        # Add log record if it is unique
        # or modify count and last seen time otherwise
        async with self._lock:
            entry = self._accumulated_records.get(signature)
            if entry is None:
                self._accumulated_records[signature] = {
                    "signature": signature,
                    "count": 1,
                    "first_seen": time_now,
                    "last_seen": time_now,
                    "level": level,
                    "name": name,
                    "source": source,
                    "message": message,
                }
            else:
                entry["count"] += 1
                entry["last_seen"] = time_now

    async def _flush(self, _=None) -> None:
        """Send one accumulated report per time window"""
        async with self._lock:

            # If there were no logs, restart the timer
            if not self._accumulated_records:
                self._period_start = dt_util.utcnow()
                _LOGGER.debug(
                    "LoggerHandler did not found any significant logs"
                )
                return

            period_end = dt_util.utcnow()

            entries = list(self._accumulated_records.values())

            # Statistics
            total_number = sum(entry["count"] for entry in entries)
            unique_number = len(entries)

            # Sort by occurrence and keep only top 25
            entries.sort(key=lambda entry: entry["count"], reverse=True)
            top_entries = entries[:25]

            # Calc occurrences by level
            by_level_events: dict[str, int] = {}
            for entry in entries:
                level = entry.get("level") or "UNKNOWN"
                by_level_events[level] = (
                    by_level_events.get(level, 0) + int(entry.get("count", 0))
                )

            # Gather issue
            issue: dict[str, Any] = {
                "type": "accumulated_system_log_problems",
                "schema_version": 1,
                "ts_start": self._period_start.isoformat(),
                "ts_end": period_end.isoformat(),
                "summary": (
                    f"System log: {unique_number} unique issues, "
                    f"{total_number} occurrences "
                    f"(last {CHECK_LOGS_TIMEOUT} min)"
                ),
                "details": {
                    "logs_timeout_minutes": CHECK_LOGS_TIMEOUT,
                    "total_events": total_number,
                    "unique_events": unique_number,
                    "by_level_events": by_level_events,
                    "top_events": top_entries,
                },
            }

            # Reset buffer for next time window
            self._accumulated_records = {}
            self._period_start = period_end

        # Outside acyncio lock, trigger report sending
        _LOGGER.debug(
            "LoggerHandler is sending report (unique=%d, total=%d)",
            unique_number, total_number
        )
        await self._send_report(issue)
