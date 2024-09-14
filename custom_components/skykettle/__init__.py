"""Support for SkyKettle."""
import logging
from datetime import timedelta

import homeassistant.helpers.event as ev
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (ATTR_SW_VERSION, CONF_DEVICE,
                                 CONF_FRIENDLY_NAME, CONF_MAC, CONF_PASSWORD,
                                 CONF_SCAN_INTERVAL, Platform)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.entity import DeviceInfo

from .const import *
from .kettle_connection import KettleConnection

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.WATER_HEATER,
    Platform.SWITCH,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Sky Kettle integration from a config entry."""
    entry.async_on_unload(entry.add_update_listener(entry_update_listener))

    if DOMAIN not in hass.data: hass.data[DOMAIN] = {}
    if entry.entry_id not in hass.data: hass.data[DOMAIN][entry.entry_id] = {}

    kettle = KettleConnection(
        mac=entry.data[CONF_MAC],
        key=entry.data[CONF_PASSWORD],
        persistent=entry.data[CONF_PERSISTENT_CONNECTION],
        adapter=entry.data.get(CONF_DEVICE, None),
        hass=hass,
        model=entry.data.get(CONF_FRIENDLY_NAME, None)
    )
    hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION] = kettle

    async def poll(now, **kwargs) -> None:
        await kettle.update()
        await hass.async_add_executor_job(dispatcher_send, hass, DISPATCHER_UPDATE)
        if hass.data[DOMAIN][DATA_WORKING]:
            schedule_poll(timedelta(seconds=entry.data[CONF_SCAN_INTERVAL]))
        else:
            _LOGGER.info("Not working anymore, stop")

    def schedule_poll(td):
        hass.data[DOMAIN][DATA_CANCEL] = ev.async_call_later(hass, td, poll)

    hass.data[DOMAIN][DATA_WORKING] = True
    hass.data[DOMAIN][DATA_DEVICE_INFO] = lambda: device_info(entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    schedule_poll(timedelta(seconds=3))

    return True

def device_info(entry):
    return DeviceInfo(
        name=(FRIENDLY_NAME + " " + entry.data.get(CONF_FRIENDLY_NAME, "")).strip(),
        manufacturer=MANUFACTORER,
        model=entry.data.get(CONF_FRIENDLY_NAME, None),
        sw_version=entry.data.get(ATTR_SW_VERSION, None),
        identifiers={
            (DOMAIN, entry.data[CONF_MAC])
        },
        connections={
            ("mac", entry.data[CONF_MAC])
        }
    )

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.debug("Unloading")
    hass.data[DOMAIN][DATA_WORKING] = False
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_unload(entry, component)
        )
    hass.data[DOMAIN][DATA_CANCEL]()
    await hass.async_add_executor_job(hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION].stop)
    hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION] = None
    _LOGGER.debug("Entry unloaded")
    return True

async def entry_update_listener(hass, entry):
    """Handle options update."""
    kettle = hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION]
    kettle.persistent = entry.data.get(CONF_PERSISTENT_CONNECTION)
    _LOGGER.debug("Options updated")
