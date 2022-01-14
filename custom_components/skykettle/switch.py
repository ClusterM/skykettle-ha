"""Demo platform that has two fake switches.""""""SkyKettle."""
import logging

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.const import *

from .skykettle import SkyKettle
from .const import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the SkyKettle entry."""
    async_add_entities([SkySwitch(hass, entry)])


class SkySwitch(SwitchEntity):
    """Representation of a demo switch."""

    def __init__(self, hass, entry):
        """Initialize the switch device."""
        self.hass = hass
        self.entry = entry

    async def async_added_to_hass(self):
        self.update()
        self.async_on_remove(async_dispatcher_connect(self.hass, DISPATCHER_UPDATE, self.update))

    def update(self):
        self.schedule_update_ha_state()

    @property
    def kettle(self):
        return self.hass.data[DOMAIN][self.entry.entry_id][DATA_CONNECTION]

    @property
    def name(self):
        """Name of the entity."""
        return FRIENDLY_NAME

    @property
    def device_class(self):
        return SwitchDeviceClass.SWITCH

    @property
    def icon(self):
        return "mdi:kettle"

    @property
    def device_info(self):
        model = self.entry.data.get(ATTR_MODEL, None)
        sw_version = self.entry.data.get(ATTR_SW_VERSION, None)
        return DeviceInfo(
            manufacturer=MANUFACTORER,
            model=model,
            sw_version=sw_version,
            identifiers={
                (DOMAIN, self.entry.data[CONF_MAC])
            },
            connections={                
                ("mac", self.entry.data[CONF_MAC])
            },
            suggested_area=SUGGESTED_AREA
        )

    @property
    def should_poll(self):
        return False
    
    @property
    def assumed_state(self):
        return False

    @property
    def available(self):
        return self.kettle.available
    
    @property
    def unique_id(self):
        return self.entry.entry_id + "_switch"

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        return self.kettle.current_mode != None
    
    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.kettle.set_target_mode(SkyKettle.MODE_BOIL)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.kettle.set_target_mode(None)
