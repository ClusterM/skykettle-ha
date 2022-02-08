"""Config flow for Sky Kettle integration."""
import logging
import re
import secrets
import traceback
import voluptuous as vol
from homeassistant.const import *
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.core import callback
from .const import *
from .ble_scan import ble_scan
from .kettle_connection import KettleConnection

_LOGGER = logging.getLogger(__name__)


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
        # _LOGGER.debug(f"initial config: {self.config}")

    async def init_mac(self, mac):
        mac = mac.upper()
        mac = mac.replace(':','').replace('-','').replace(' ','')
        mac = ':'.join([mac[p*2:(p*2)+2] for p in range(6)])
        id = f"{DOMAIN}-{mac}"
        if id in self._async_current_ids():
            return False
        await self.async_set_unique_id(id)
        self.config[CONF_MAC] = mac
        # It's time to create random password
        self.config[CONF_PASSWORD] = list(secrets.token_bytes(8))
        return True

    async def async_step_user(self, user_input=None):
        """Handle the user step."""

        if user_input is not None:
            return await self.async_step_scan()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({})
        )

    async def async_step_scan(self, user_input=None):
        """Handle the scan step."""

        errors = {}
        if user_input is not None:
            if user_input[CONF_MAC] == "...": return await self.async_step_manual_mac()
            spl = user_input[CONF_MAC].split(' ', maxsplit=2)
            mac = spl[0]
            name = spl[1][1:-2] if len(spl) >= 2 else None
            if not await self.init_mac(mac): return self.async_abort(reason='already_configured')
            if name: self.config[CONF_FRIENDLY_NAME] = name
            # Continue to options
            return await self.async_step_connect()

        try:
            macs = await ble_scan(scan_time=BLE_SCAN_TIME)
            _LOGGER.debug(f"Scan result: {macs}")
            macs_filtered = [mac for mac in macs if mac.name and mac.name.startswith("RK-")]
            if len(macs_filtered) > 0:
                macs = macs_filtered
                _LOGGER.debug(f"Filtered scan result: {macs}")
            if len(macs) == 0:
                errors["base"] = "no_scan"
            mac_list = [f"{r.mac} ({r.name})" for r in macs]
            mac_list = mac_list + ["..."] # Manual
            schema = vol.Schema(
            {
                vol.Required(CONF_MAC): vol.In(mac_list)
            })
        except PermissionError:
            _LOGGER.error(traceback.format_exc())
            return self.async_abort(reason='permission_error')
        except FileNotFoundError:
            _LOGGER.error(traceback.format_exc())
            return self.async_abort(reason='hcitool_not_found')
        except Exception:
            _LOGGER.error(traceback.format_exc())
            return self.async_abort(reason='unknown')
        return self.async_show_form(
            step_id="scan",
            errors=errors,
            data_schema=schema
        )

    async def async_step_manual_mac(self, user_input=None):
        """Handle the manual_mac step."""
        errors = {}
        if user_input is not None:
            mac = user_input[CONF_MAC]
            if re.match(REGEX_MAC, mac):
                if not await self.init_mac(mac): return self.async_abort(reason='already_configured')
            else:
                errors[CONF_MAC] = "invalid_mac"
            if not errors:
                # Continue to options
                return await self.async_step_connect()

        MAC_SCHEMA = vol.Schema(
        {
            vol.Required(CONF_MAC): cv.string,
        })
        return self.async_show_form(
            step_id="manual_mac",
            errors=errors,
            data_schema=MAC_SCHEMA
        )

    async def async_step_connect(self, user_input=None):
        """Handle the connect step."""
        errors = {}
        kettle = KettleConnection(
            mac=self.config[CONF_MAC],
            key=self.config[CONF_PASSWORD],
            persistent=True
        )
        tries = 3
        while tries > 0 and not kettle._last_connect_ok:
            await kettle.update()
            tries = tries - 1
            
        connect_ok = kettle._last_connect_ok
        auth_ok = kettle._last_auth_ok
        
        if not connect_ok:
            errors["base"] = "cant_connect"
        elif auth_ok:
            return await self.async_step_init()
        elif user_input != None:
            errors["base"] = "cant_auth"

        return self.async_show_form(
            step_id="connect",
            errors=errors,
            data_schema=vol.Schema({})
        )  

    async def async_step_init(self, user_input=None):
        """Handle the options step."""
        errors = {}
        if user_input is not None:
            self.config[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]
            self.config[CONF_PERSISTENT_CONNECTION] = user_input[CONF_PERSISTENT_CONNECTION]
            fname = f"{self.config.get(CONF_FRIENDLY_NAME, FRIENDLY_NAME)} ({self.config[CONF_MAC]})"
            # _LOGGER.debug(f"saving config: {self.config}")
            if self.entry:
                self.hass.config_entries.async_update_entry(self.entry, data=self.config)
            _LOGGER.info(f"Config saved")
            return self.async_create_entry(
                title=fname, data=self.config if not self.entry else {}
            )

        schema = vol.Schema(
        {
            vol.Required(CONF_PERSISTENT_CONNECTION, default=self.config.get(CONF_PERSISTENT_CONNECTION, DEFAULT_PERSISTENT_CONNECTION)): cv.boolean,
            vol.Required(CONF_SCAN_INTERVAL, default=self.config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
        })

        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=schema
        )
