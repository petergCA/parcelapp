import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, CONF_API_KEY, CONF_FILTER_MODE

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_FILTER_MODE, default="recent"): vol.In(
            ["active", "recent"]
        ),
    }
)


class ParcelAppConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
            )

        return self.async_create_entry(
            title="Parcel App",
            data={
                CONF_API_KEY: user_input[CONF_API_KEY],
                CONF_FILTER_MODE: user_input[CONF_FILTER_MODE],
            },
        )