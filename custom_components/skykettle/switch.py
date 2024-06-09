"""SkyKettle."""
import logging

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import CONF_FRIENDLY_NAME
from homeassistant.helpers.dispatcher import (async_dispatcher_connect,
                                              dispatcher_send)
from homeassistant.helpers.entity import EntityCategory

from .const import *
from .skykettle import SkyKettle

_LOGGER = logging.getLogger(__name__)


SWITCH_MAIN = "switch"
SWITCH_SOUND = "sound"
SWITCH_LIGHT_SYNC = "light_sync"
SWITCH_LIGHT_BOIL = "light_boil"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the SkyKettle entry."""
    model_code = hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION].model_code
    async_add_entities([
        SkySwitch(hass, entry, SWITCH_MAIN)
    ])
    if model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
        async_add_entities([
            SkySwitch(hass, entry, SWITCH_SOUND),
            SkySwitch(hass, entry, SWITCH_LIGHT_SYNC),
            SkySwitch(hass, entry, SWITCH_LIGHT_BOIL),
        ])


class SkySwitch(SwitchEntity):
    """Representation of a SkyKettle switch device."""

    def __init__(self, hass, entry, switch_type):
        """Initialize the switch device."""
        self.hass = hass
        self.entry = entry
        self.switch_type = switch_type

    async def async_added_to_hass(self):
        self.update()
        self.async_on_remove(async_dispatcher_connect(self.hass, DISPATCHER_UPDATE, self.update))

    def update(self):
        self.schedule_update_ha_state()

    @property
    def kettle(self):
        return self.hass.data[DOMAIN][self.entry.entry_id][DATA_CONNECTION]

    @property
    def unique_id(self):
        return f"{self.entry.entry_id}_{self.switch_type}"

    @property
    def name(self):
        """Name of the entity."""
        if self.switch_type == SWITCH_MAIN:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip()
        if self.switch_type == SWITCH_SOUND:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " enable sound"
        if self.switch_type == SWITCH_LIGHT_SYNC:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " enable sync light"
        if self.switch_type == SWITCH_LIGHT_BOIL:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " enable boil light"

    @property
    def icon(self):
        if self.switch_type == SWITCH_MAIN:
            return "mdi:cog"
        if self.switch_type == SWITCH_SOUND:
            return "mdi:volume-high"
        if self.switch_type == SWITCH_LIGHT_SYNC:
            return "mdi:sync"
        if self.switch_type == SWITCH_LIGHT_BOIL:
            return "mdi:alarm-light"

    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH

    @property
    def device_info(self):
        return self.hass.data[DOMAIN][DATA_DEVICE_INFO]()

    @property
    def should_poll(self):
        return False

    @property
    def assumed_state(self):
        return False

    @property
    def available(self):        
        if self.switch_type == SWITCH_MAIN:
            return self.kettle.available
        if self.switch_type == SWITCH_SOUND:
            return self.kettle.available and self.kettle.sound_enabled != None
        if self.switch_type == SWITCH_LIGHT_SYNC:
            return self.kettle.available and self.kettle.light_switch_sync != None
        if self.switch_type == SWITCH_LIGHT_BOIL:
            return self.kettle.available and self.kettle.light_switch_boil != None

    @property
    def entity_category(self):
        if self.switch_type == SWITCH_MAIN:
            return None
        if self.switch_type == SWITCH_SOUND:
            return EntityCategory.CONFIG
        if self.switch_type == SWITCH_LIGHT_SYNC:
            return EntityCategory.CONFIG
        if self.switch_type == SWITCH_LIGHT_BOIL:
            return EntityCategory.CONFIG

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        if self.switch_type == SWITCH_MAIN:
            return self.kettle.target_mode != None
        if self.switch_type == SWITCH_SOUND:
            return self.kettle.sound_enabled
        if self.switch_type == SWITCH_LIGHT_SYNC:
            return self.kettle.light_switch_sync
        if self.switch_type == SWITCH_LIGHT_BOIL:
            return self.kettle.light_switch_boil

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        if self.switch_type == SWITCH_MAIN:
            await self.kettle.set_target_mode(SkyKettle.MODE_NAMES[SkyKettle.MODE_BOIL])
        if self.switch_type == SWITCH_SOUND:
            await self.kettle.set_sound(True)
        if self.switch_type == SWITCH_LIGHT_SYNC:
            await self.kettle.set_light_switch(SkyKettle.LIGHT_SYNC, True)
        if self.switch_type == SWITCH_LIGHT_BOIL:
            await self.kettle.set_light_switch(SkyKettle.LIGHT_BOIL, True)
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        if self.switch_type == SWITCH_MAIN:
            await self.kettle.set_target_mode(None)
        if self.switch_type == SWITCH_SOUND:
            await self.kettle.set_sound(False)
        if self.switch_type == SWITCH_LIGHT_SYNC:
            await self.kettle.set_light_switch(SkyKettle.LIGHT_SYNC, False)
        if self.switch_type == SWITCH_LIGHT_BOIL:
            await self.kettle.set_light_switch(SkyKettle.LIGHT_BOIL, False)
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)
