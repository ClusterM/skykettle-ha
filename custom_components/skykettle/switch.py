"""SkyKettle."""
import logging

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect
from homeassistant.const import *

from .skykettle import SkyKettle
from .const import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the SkyKettle entry."""
    async_add_entities([SkySwitch(hass, entry)])


class SkySwitch(SwitchEntity):
    """Representation of a SkyKettle switch device."""

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
    def unique_id(self):
        return f"{self.entry.entry_id}_switch"

    @property
    def name(self):
        """Name of the entity."""
        return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " switch"

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
        return self.kettle.available

    @property
    def entity_category(self):
        return None

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        return self.kettle.target_mode != None

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.kettle.set_target_mode(SkyKettle.MODE_NAMES[SkyKettle.MODE_BOIL])
        async_dispatcher_send(self.hass, DISPATCHER_UPDATE)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.kettle.set_target_mode(None)
        async_dispatcher_send(self.hass, DISPATCHER_UPDATE)
