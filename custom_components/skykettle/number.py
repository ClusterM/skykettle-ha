"""SkyKettle."""
import logging

from homeassistant.components.number import NumberMode, NumberEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect
from homeassistant.const import *

from .skykettle import SkyKettle
from .const import *

_LOGGER = logging.getLogger(__name__)


NUMBER_TYPE_BOIL_TIME = "boil_time"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the SkyKettle entry."""
    async_add_entities([
        SkyNumber(hass, entry, NUMBER_TYPE_BOIL_TIME)
    ])


class SkyNumber(NumberEntity):
    """Representation of a SkyKettle number device."""

    def __init__(self, hass, entry, number_type):
        """Initialize the number device."""
        self.hass = hass
        self.entry = entry
        self.number_type = number_type

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
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return f"{self.entry.entry_id}_boil_time"

    @property
    def name(self):
        """Name of the entity."""
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " boil time"

    @property
    def icon(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return "mdi:kettle-steam"

    @property
    def device_class(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return None # No classes

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
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return self.kettle.available

    @property
    def entity_category(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return EntityCategory.CONFIG

    @property
    def value(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return self.kettle.boil_time

    @property
    def min_value(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return -5

    @property
    def max_value(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return 5

    @property
    def step(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return 1

    @property
    def mode(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return NumberMode.SLIDER

    async def async_set_value(self, value):
        await self.kettle.set_boil_time(value)
        async_dispatcher_send(self.hass, DISPATCHER_UPDATE)
