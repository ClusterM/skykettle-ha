"""Config flow for Sky Kettle integration."""
import logging
import re
import voluptuous as vol
from homeassistant.const import *
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.core import callback
from .const import *
import secrets

_LOGGER = logging.getLogger(__name__)

MAC_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC, description={"suggested_value": "D4:3D:56:6C:DA:A4"}): cv.string,
    }
)

class SkyKettleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Wake cv.matches_regexon LAN integration."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        """Get options flow for this handler."""
        return SkyKettleConfigFlow(entry=entry)

    def __init__(self, entry = None):
        """Initialize a new SkyKettleConfigFlow."""
        self.entry = entry
        self.config = {} if not entry else dict(entry.data.items())
        _LOGGER.debug(f"initial config: {self.config}")

    def get_options_schema(self):
        return vol.Schema(
        {
            vol.Required(CONF_SCAN_INTERVAL, default=self.config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
            vol.Required(CONF_PERSISTENT_CONNECTION, default=self.config.get(CONF_PERSISTENT_CONNECTION, DEFAULT_PERSISTENT_CONNECTION)): cv.boolean,
        })
        
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            mac = user_input[CONF_MAC]
            if re.match(REGEX_MAC, mac):
                mac = mac.upper()
                mac = mac.replace(':','').replace('-','').replace(' ','')
                mac = ':'.join([mac[p*2:(p*2)+2] for p in range(6)])
                id = f"{DOMAIN}-{mac}"
                if id in self._async_current_ids():
                    return self.async_abort(reason='already_configured')
                await self.async_set_unique_id(id)
                self.config[CONF_MAC] = mac
                self.config[CONF_PASSWORD] = list(secrets.token_bytes(8))
            else:
                errors[CONF_MAC] = "invalid_mac"
            if not errors:
                return self.async_show_form(step_id="init", data_schema=self.get_options_schema())

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=MAC_SCHEMA
        )

    async def async_step_init(self, user_input=None):
        """Handle the options step."""
        errors = {}
        if user_input is not None:            
            self.config[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]            
            self.config[CONF_PERSISTENT_CONNECTION] = user_input[CONF_PERSISTENT_CONNECTION]            
            fname = f"{FRIENDLY_NAME} ({self.config[CONF_MAC]})"
            _LOGGER.debug(f"saving config: {self.config}")
            if self.entry:
                self.hass.config_entries.async_update_entry(self.entry, data=self.config)
            return self.async_create_entry(
                title=fname, data=self.config if not self.entry else {}
            )

        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=self.get_options_schema()
        )
