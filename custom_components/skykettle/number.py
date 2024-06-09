"""SkyKettle."""
import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import (CONF_FRIENDLY_NAME, UnitOfTemperature,
                                 UnitOfTime)
from homeassistant.helpers.dispatcher import (async_dispatcher_connect,
                                              dispatcher_send)
from homeassistant.helpers.entity import EntityCategory

from .const import *
from .skykettle import SkyKettle

_LOGGER = logging.getLogger(__name__)


NUMBER_TYPE_BOIL_TIME = "boil_time"
NUMBER_TEMPERATURE_LOW = "temp_low"
NUMBER_TEMPERATURE_MID = "temp_mid"
NUMBER_TEMPERATURE_HIGH = "temp_high"
NUMBER_COLOR_INTERVAL = "color_interval"
NUMBER_LAMP_AUTO_OFF_HOURS = "lamp_auto_off_hours"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the SkyKettle entry."""
    model_code = hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION].model_code
    if model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
        async_add_entities([
            SkyNumber(hass, entry, NUMBER_TYPE_BOIL_TIME),
            SkyNumber(hass, entry, NUMBER_TEMPERATURE_LOW),
            SkyNumber(hass, entry, NUMBER_TEMPERATURE_MID),
            SkyNumber(hass, entry, NUMBER_TEMPERATURE_HIGH),
            SkyNumber(hass, entry, NUMBER_COLOR_INTERVAL),
            SkyNumber(hass, entry, NUMBER_LAMP_AUTO_OFF_HOURS),
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
        return f"{self.entry.entry_id}_{self.number_type}"

    @property
    def name(self):
        """Name of the entity."""
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " boil time"
        if self.number_type == NUMBER_TEMPERATURE_LOW:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " temperature #1"
        if self.number_type == NUMBER_TEMPERATURE_MID:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " temperature #2"
        if self.number_type == NUMBER_TEMPERATURE_HIGH:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " temperature #3"
        if self.number_type == NUMBER_COLOR_INTERVAL:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " lamp color change interval"
        if self.number_type == NUMBER_LAMP_AUTO_OFF_HOURS:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " lamp auto off time"

    @property
    def icon(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return "mdi:kettle-steam"
        if self.number_type == NUMBER_TEMPERATURE_LOW:
            return "mdi:thermometer-low"
        if self.number_type == NUMBER_TEMPERATURE_MID:
            return "mdi:thermometer"
        if self.number_type == NUMBER_TEMPERATURE_HIGH:
            return "mdi:thermometer-high"
        if self.number_type == NUMBER_COLOR_INTERVAL:
            return "mdi:timer"
        if self.number_type == NUMBER_LAMP_AUTO_OFF_HOURS:
            return "mdi:timer-sand"

    @property
    def device_class(self):
        if self.number_type in [NUMBER_TEMPERATURE_LOW, NUMBER_TEMPERATURE_MID, NUMBER_TEMPERATURE_HIGH]:
            return "temperature"
        return None

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
            return self.kettle.available and self.kettle.boil_time != None
        if self.number_type == NUMBER_TEMPERATURE_LOW:
            return self.kettle.available and self.kettle.get_temperature(SkyKettle.LIGHT_BOIL, 0) != None
        if self.number_type == NUMBER_TEMPERATURE_MID:
            return self.kettle.available and self.kettle.get_temperature(SkyKettle.LIGHT_BOIL, 1) != None
        if self.number_type == NUMBER_TEMPERATURE_HIGH:
            return self.kettle.available and self.kettle.get_temperature(SkyKettle.LIGHT_BOIL, 2) != None
        if self.number_type == NUMBER_COLOR_INTERVAL:
            return self.kettle.available and self.kettle.color_interval != None
        if self.number_type == NUMBER_LAMP_AUTO_OFF_HOURS:
            return self.kettle.available and self.kettle.lamp_auto_off_hours != None

    @property
    def entity_category(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return EntityCategory.CONFIG
        if self.number_type == NUMBER_TEMPERATURE_LOW:
            return EntityCategory.CONFIG
        if self.number_type == NUMBER_TEMPERATURE_MID:
            return EntityCategory.CONFIG
        if self.number_type == NUMBER_TEMPERATURE_HIGH:
            return EntityCategory.CONFIG
        if self.number_type == NUMBER_COLOR_INTERVAL:
            return EntityCategory.CONFIG
        if self.number_type == NUMBER_LAMP_AUTO_OFF_HOURS:
            return EntityCategory.CONFIG

    @property
    def native_unit_of_measurement(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return None
        if self.number_type == NUMBER_TEMPERATURE_LOW:
            return UnitOfTemperature.CELSIUS
        if self.number_type == NUMBER_TEMPERATURE_MID:
            return UnitOfTemperature.CELSIUS
        if self.number_type == NUMBER_TEMPERATURE_HIGH:
            return UnitOfTemperature.CELSIUS
        if self.number_type == NUMBER_COLOR_INTERVAL:
            return "secs"
        if self.number_type == NUMBER_LAMP_AUTO_OFF_HOURS:
            return UnitOfTime.HOURS

    @property
    def native_value(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return self.kettle.boil_time
        if self.number_type == NUMBER_TEMPERATURE_LOW:
            return self.kettle.get_temperature(SkyKettle.LIGHT_BOIL, 0)
        if self.number_type == NUMBER_TEMPERATURE_MID:
            return self.kettle.get_temperature(SkyKettle.LIGHT_BOIL, 1)
        if self.number_type == NUMBER_TEMPERATURE_HIGH:
            return self.kettle.get_temperature(SkyKettle.LIGHT_BOIL, 2)
        if self.number_type == NUMBER_COLOR_INTERVAL:
            return self.kettle.color_interval
        if self.number_type == NUMBER_LAMP_AUTO_OFF_HOURS:
            return self.kettle.lamp_auto_off_hours

    @property
    def native_min_value(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return -5
        if self.number_type == NUMBER_TEMPERATURE_LOW:
            return 0
        if self.number_type == NUMBER_TEMPERATURE_MID:
            return self.kettle.get_temperature(SkyKettle.LIGHT_BOIL, 0)
        if self.number_type == NUMBER_TEMPERATURE_HIGH:
            return self.kettle.get_temperature(SkyKettle.LIGHT_BOIL, 1)
        if self.number_type == NUMBER_COLOR_INTERVAL:
            return 30
        if self.number_type == NUMBER_LAMP_AUTO_OFF_HOURS:
            return 1

    @property
    def native_max_value(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return 5
        if self.number_type == NUMBER_TEMPERATURE_LOW:
            return self.kettle.get_temperature(SkyKettle.LIGHT_BOIL, 1)
        if self.number_type == NUMBER_TEMPERATURE_MID:
            return self.kettle.get_temperature(SkyKettle.LIGHT_BOIL, 2)
        if self.number_type == NUMBER_TEMPERATURE_HIGH:
            return 100
        if self.number_type == NUMBER_COLOR_INTERVAL:
            return 180
        if self.number_type == NUMBER_LAMP_AUTO_OFF_HOURS:
            return 24

    @property
    def native_step(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return 1
        if self.number_type == NUMBER_TEMPERATURE_LOW:
            return 5
        if self.number_type == NUMBER_TEMPERATURE_MID:
            return 5
        if self.number_type == NUMBER_TEMPERATURE_HIGH:
            return 5
        if self.number_type == NUMBER_COLOR_INTERVAL:
            return 10
        if self.number_type == NUMBER_LAMP_AUTO_OFF_HOURS:
            return 1

    @property
    def mode(self):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            return NumberMode.SLIDER
        if self.number_type == NUMBER_TEMPERATURE_LOW:
            return NumberMode.BOX
        if self.number_type == NUMBER_TEMPERATURE_MID:
            return NumberMode.BOX
        if self.number_type == NUMBER_TEMPERATURE_HIGH:
            return NumberMode.BOX
        if self.number_type == NUMBER_COLOR_INTERVAL:
            return NumberMode.BOX
        if self.number_type == NUMBER_LAMP_AUTO_OFF_HOURS:
            return NumberMode.BOX

    async def async_set_native_value(self, value):
        if self.number_type == NUMBER_TYPE_BOIL_TIME:
            await self.kettle.set_boil_time(value)
        if self.number_type == NUMBER_TEMPERATURE_LOW:
            await self.kettle.set_temperature(SkyKettle.LIGHT_BOIL, 0, value)
        if self.number_type == NUMBER_TEMPERATURE_MID:
            await self.kettle.set_temperature(SkyKettle.LIGHT_BOIL, 1, value)
        if self.number_type == NUMBER_TEMPERATURE_HIGH:
            await self.kettle.set_temperature(SkyKettle.LIGHT_BOIL, 2, value)
        if self.number_type == NUMBER_COLOR_INTERVAL:
            await self.kettle.set_lamp_color_interval(value)
        if self.number_type == NUMBER_LAMP_AUTO_OFF_HOURS:
            await self.kettle.set_lamp_auto_off_hours(value)
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)
