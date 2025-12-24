import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from .const import (
    DOMAIN,
    CONF_SENDER_SEED,
    CONF_INTEGRATOR_ADDRESS,
    CONF_PINATA_SECRET,
    CONF_PINATA_PUBLIC,
    )

from .robonomics import Robonomics

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_INTEGRATOR_ADDRESS): str,
        vol.Required(CONF_PINATA_SECRET): str,
        vol.Required(CONF_PINATA_PUBLIC): str,
    }
)


class ReportServiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Handle a config flow for the Report Service during integration setup.

    The class object exists only for the duration of the setup wizard,
    and the result is a ConfigEntry that lives permanently.
    """

    # The schema version of the entries that it creates
    # HA will call migrate method if the version changes
    VERSION = 1

    def __init__(self):
        self.seed_saved = False
        self.user_data = {}

    async def async_step_user(
            self,
            user_input: dict[str, Any] | None = None
            ) -> ConfigFlowResult:
        """
        The initial step of the configuration
        """

        # Since it is needed exactly one integration instance, then assign
        # a unique ID to the flow and abort the flow if another flow
        # with the same unique ID is in progress
        await self.async_set_unique_id(DOMAIN)

        # Abort the flow if a config entry with the same unique ID exists
        self._abort_if_unique_id_configured()

        # Show the form to enter intergrator and Pinata data
        # if it hasn't already been done, then save data in user_data
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )
        self.user_data = user_input

        sender_seed = Robonomics.generate_seed()
        self.user_data[CONF_SENDER_SEED] = sender_seed
        return await self.async_step_seed()

    async def async_step_seed(
            self,
            user_input: dict[str, Any] | None = None
            ) -> ConfigFlowResult:
        """
        Show the seed to user and configure Robonomics
        """

        # Show the form with the seed if it hasn't already been done
        if not self.seed_saved:
            self.seed_saved = True
            return self.async_show_form(
                step_id="seed",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "seed": self.user_data[CONF_SENDER_SEED]
                    },
            )

        # Save config as persistent ConfigEntry in HA
        return self.async_create_entry(
            title="Robonomics Report Service", data=self.user_data
        )
