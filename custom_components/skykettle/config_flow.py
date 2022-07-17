"""Config flow for Sky Kettle integration."""
import logging
import re
import secrets
import traceback
import sys
import subprocess
import voluptuous as vol
from homeassistant.const import *
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.core import callback
from .const import *
from .ble_scan import ble_scan
from .ble_scan import ble_get_adapters
from .kettle_connection import KettleConnection
from .skykettle import SkyKettle

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
        # Check OS
        if sys.platform != "linux":
            return self.async_abort(reason='linux_not_found')
        # Test binaries
        try:
            subprocess.Popen(["timeout"], shell=False).kill()
        except FileNotFoundError:
            _LOGGER.error(traceback.format_exc())
            return self.async_abort(reason='timeout_not_found')
        try:
            subprocess.Popen(["gatttool"], shell=False).kill()
        except FileNotFoundError:
            _LOGGER.error(traceback.format_exc())
            return self.async_abort(reason='gatttool_not_found')
        try:
            subprocess.Popen(["hcitool"], shell=False).kill()
        except FileNotFoundError:
            _LOGGER.error(traceback.format_exc())
            return self.async_abort(reason='hcitool_not_found')
        return await self.async_step_select_adapter()

    async def async_step_select_adapter(self, user_input=None):
        """Handle the select_adapter step."""
        errors = {}
        if user_input is not None:
            spl = user_input[CONF_DEVICE].split(' ', maxsplit=1)
            name = None
            if spl[0] != "auto": name = spl[0]
            self.config[CONF_DEVICE] = name
            # Continue to scan
            return await self.async_step_scan_message()

        try:
            adapters = await ble_get_adapters()
            _LOGGER.debug(f"Adapters: {adapters}")
            adapters_list = [f"{r.name} ({r.mac})" for r in adapters]
            adapters_list = ["auto"] + adapters_list # Auto
            schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE): vol.In(adapters_list)
            })
        except Exception:
            _LOGGER.error(traceback.format_exc())
            return self.async_abort(reason='unknown')
        return self.async_show_form(
            step_id="select_adapter",
            errors=errors,
            data_schema=schema
        )
    
    async def async_step_scan_message(self, user_input=None):
        """Handle the scan_message step."""
        if user_input is not None:
            return await self.async_step_scan()
        return self.async_show_form(
            step_id="scan_message",
            data_schema=vol.Schema({})
        )

    async def async_step_scan(self, user_input=None):
        """Handle the scan step."""
        errors = {}
        if user_input is not None:
            spl = user_input[CONF_MAC].split(' ', maxsplit=1)
            mac = spl[0]
            name = spl[1][1:-1] if len(spl) >= 2 else None
            if not await self.init_mac(mac):
                # This kettle already configured
                return self.async_abort(reason='already_configured')
            if name: self.config[CONF_FRIENDLY_NAME] = name
            # Continue to connect step
            return await self.async_step_connect()

        try:
            macs = await ble_scan(self.config.get(CONF_DEVICE, None), scan_time=BLE_SCAN_TIME)
            _LOGGER.debug(f"Scan result: {macs}")
            macs_filtered = [mac for mac in macs if SkyKettle.get_model_code(mac.name)]
            if len(macs_filtered) == 0:
                return self.async_abort(reason='kettle_not_found')
            mac_list = [f"{r.mac} ({r.name})" for r in macs_filtered]
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

    async def async_step_connect(self, user_input=None):
        """Handle the connect step."""
        errors = {}
        if user_input is not None:
            kettle = KettleConnection(
                mac=self.config[CONF_MAC],
                key=self.config[CONF_PASSWORD],
                persistent=True,
                adapter=self.config.get(CONF_DEVICE, None),
                hass=self.hass,
                model=self.config.get(CONF_FRIENDLY_NAME, None)
            )
            tries = 3
            while tries > 0 and not kettle._last_connect_ok:
                await kettle.update()
                tries = tries - 1
            
            connect_ok = kettle._last_connect_ok
            auth_ok = kettle._last_auth_ok
            kettle.stop()
        
            if not connect_ok:
                errors["base"] = "cant_connect"
            elif not auth_ok:
                errors["base"] = "cant_auth"
            else:
                return await self.async_step_init()

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
