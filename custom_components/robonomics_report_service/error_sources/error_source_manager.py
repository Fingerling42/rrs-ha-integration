from homeassistant.core import HomeAssistant, callback

from .sources import EntitiesStatusChecker, ErrorSource, LoggerHandler


class ErrorSourcesManager:
    """Class to manage different watchers for errors"""
    def __init__(self, hass: HomeAssistant):
        self.error_sources: list[ErrorSource] = [
            # EntitiesStatusChecker(hass),
            LoggerHandler(hass)
        ]

    @callback
    def setup_sources(self) -> None:
        """Start all watchers"""
        for source in self.error_sources:
            source.setup()

    @callback
    def remove_sources(self) -> None:
        """Stop all watchers"""
        for source in self.error_sources:
            source.remove()
