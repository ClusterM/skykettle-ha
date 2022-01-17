"""Support for SkyKettle."""
import logging
from .const import *
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import *
import homeassistant.helpers.event as ev
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from .kettle_connection import KettleConnection
from datetime import timedelta

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.WATER_HEATER,
    Platform.SWITCH,
    Platform.LIGHT
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Sky Kettle integration from a config entry."""
    entry.async_on_unload(entry.add_update_listener(entry_update_listener))

    if DOMAIN not in hass.data: hass.data[DOMAIN] = {}
    if entry.entry_id not in hass.data: hass.data[DOMAIN][entry.entry_id] = {}

    kettle = KettleConnection(
        entry.data[CONF_MAC],
        entry.data[CONF_PASSWORD],
        entry.data[CONF_PERSISTENT_CONNECTION]
    )
    hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION] = kettle

    async def poll(now, **kwargs) -> None:
        await kettle.update()
        async_dispatcher_send(hass, DISPATCHER_UPDATE)
        if hass.data[DOMAIN][DATA_WORKING]:
            hass.data[DOMAIN][DATA_CANCEL] = ev.async_call_later(
                hass, timedelta(seconds=entry.data[CONF_SCAN_INTERVAL]), poll)

    hass.data[DOMAIN][DATA_WORKING] = True
    hass.data[DOMAIN][DATA_CANCEL] = ev.async_call_later(
        hass, timedelta(seconds=1), poll)
    hass.data[DOMAIN][DATA_DEVICE_INFO] = lambda: device_info(entry)

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True

def device_info(entry):
    return DeviceInfo(
        name=entry.data.get(CONF_FRIENDLY_NAME, FRIENDLY_NAME),
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
    hass.data[DOMAIN][DATA_WORKING] = False
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_unload(entry, component)
        )
    hass.data[DOMAIN][DATA_CANCEL]()
    await hass.async_add_executor_job(hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION].stop)
    del hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION]
    hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION] = None
    return True

async def entry_update_listener(hass, entry):
    """Handle options update."""
    kettle = hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION]
    kettle.persistent = entry.data.get(CONF_PERSISTENT_CONNECTION)
