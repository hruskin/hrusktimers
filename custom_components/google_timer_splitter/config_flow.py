"""Config flow for Google Timer Splitter."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import DOMAIN, CONF_SOURCE

_LOGGER = logging.getLogger(__name__)


class GoogleTimerSplitterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Google Timer Splitter."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # You can add validation here if needed, for now, we just create the entry
            return self.async_create_entry(title="Google Timer Splitter", data=user_input)

        # This is the form that will be displayed to the user
        data_schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor"),
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

