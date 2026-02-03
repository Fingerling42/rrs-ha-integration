from homeassistant.core import HomeAssistant, callback

from .watchers import EntitiesStatusChecker, ErrorWatcher, LoggerHandler


class ErrorWatchersManager:
    """Class to manage different watchers for errors"""
    def __init__(self, hass: HomeAssistant):
        self.error_watchers: list[ErrorWatcher] = [
            EntitiesStatusChecker(hass),
            LoggerHandler(hass)
        ]

    @callback
    def setup_watchers(self) -> None:
        """Start all watchers"""
        for watcher in self.error_watchers:
            watcher.setup()

    @callback
    def remove_watchers(self) -> None:
        """Stop all watchers"""
        for watcher in self.error_watchers:
            watcher.remove()
