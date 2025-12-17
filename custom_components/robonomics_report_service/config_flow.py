import typing as tp
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from tenacity import retry, stop_after_attempt, wait_fixed, after_log

from .const import DOMAIN, CONF_EMAIL, CONF_SENDER_SEED

from .robonomics import Robonomics
from .rws_registration import RWSRegistrationManager
from .libp2p import LibP2P

_LOGGER = logging.getLogger(__name__)


class ReportServiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Handle a config flow for the Report Service.

    The class object exists only for the duration of the setup wizard,
    and the result is a ConfigEntry that lives permanently.
    """

    # The schema version of the entries that it creates
    # HA will call migrate method if the version changes
    VERSION = 1

    def __init__(self):
        self.user_data = {}
        self.seed_saved = False

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """
        Handle the initial step of the configuration.
        """

        # Since it is needed exactly one integration instance, then assign
        # a unique ID to the flow and abort the flow if another flow
        # with the same unique ID is in progress
        await self.async_set_unique_id(DOMAIN)

        # Abort the flow if a config entry with the same unique ID exists
        self._abort_if_unique_id_configured()

        sender_seed = Robonomics.generate_seed()
        self.user_data[CONF_SENDER_SEED] = sender_seed
        return await self.async_step_seed()

    async def async_step_seed(self, user_input: dict[str, tp.Any] | None = None):
        if not self.seed_saved:
            self.seed_saved = True
            return self.async_show_form(
                step_id="seed",
                data_schema=vol.Schema({}),
                description_placeholders={"seed": self.user_data[CONF_SENDER_SEED]},
            )
        else:
            robonomics = Robonomics(
                self.hass,
                self.user_data[CONF_SENDER_SEED],
            )
            await robonomics.setup()
            libp2p = LibP2P(robonomics.sender_address)
            await self.register_with_retry(robonomics, libp2p)
            return self.async_create_entry(
                title="Robonomics Report Service", data=self.user_data
            )

    @retry(stop=stop_after_attempt(4), wait=wait_fixed(4), after=after_log(_LOGGER, logging.WARNING))
    async def register_with_retry(self, robonomics: Robonomics, libp2p: LibP2P):
        await RWSRegistrationManager.register(self.hass, robonomics, libp2p, self.user_data[CONF_EMAIL])

