"""SkyKettle."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.const import *

from .skykettle import SkyKettle
from .const import *

_LOGGER = logging.getLogger(__name__)


SENSOR_TYPE_WATER_FRESHNESS = "water_freshness"
SENSOR_TYPE_SUCCESS_RATE = "success_rate"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the SkyKettle entry."""
    model_code = hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION].model_code
    async_add_entities([
        SkySensor(hass, entry, SENSOR_TYPE_SUCCESS_RATE),
    ])
    if model_code in [SkyKettle.MODELS_4, SkyKettle.MODELS_5, SkyKettle.MODELS_6, SkyKettle.MODELS_7]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
        async_add_entities([
            SkySensor(hass, entry, SENSOR_TYPE_WATER_FRESHNESS),
        ])


class SkySensor(SensorEntity):
    """Representation of a SkyKettle sensor device."""

    def __init__(self, hass, entry, sensor_type):
        """Initialize the sensor device."""
        self.hass = hass
        self.entry = entry
        self.sensor_type = sensor_type

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
        return f"{self.entry.entry_id}_{self.sensor_type}"

    @property
    def name(self):
        """Name of the entity."""
        if self.sensor_type == SENSOR_TYPE_WATER_FRESHNESS:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " water freshness"
        if self.sensor_type == SENSOR_TYPE_SUCCESS_RATE:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " success rate"

    @property
    def icon(self):
        if self.sensor_type == SENSOR_TYPE_WATER_FRESHNESS:
            return "mdi:water-sync"
        if self.sensor_type == SENSOR_TYPE_SUCCESS_RATE:
            return "mdi:bluetooth-connect"

    @property
    def device_class(self):
        if self.sensor_type == SENSOR_TYPE_WATER_FRESHNESS:
            return None # Unusual class
        if self.sensor_type == SENSOR_TYPE_SUCCESS_RATE:
            return None # Unusual class

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
        if self.sensor_type == SENSOR_TYPE_WATER_FRESHNESS:
            return self.kettle.available and self.kettle.water_freshness_hours != None
        if self.sensor_type == SENSOR_TYPE_SUCCESS_RATE:
            return True # Always readable

    @property
    def entity_category(self):
        if self.sensor_type == SENSOR_TYPE_WATER_FRESHNESS:
            return None
        if self.sensor_type == SENSOR_TYPE_SUCCESS_RATE:
            return EntityCategory.DIAGNOSTIC

    @property
    def last_reset(self):
        return None

    @property
    def native_value(self):
        if self.sensor_type == SENSOR_TYPE_WATER_FRESHNESS:
            return self.kettle.water_freshness_hours
        if self.sensor_type == SENSOR_TYPE_SUCCESS_RATE:
            return self.kettle.success_rate

    @property
    def native_unit_of_measurement(self):
        if self.sensor_type == SENSOR_TYPE_WATER_FRESHNESS:
            return "h"
        if self.sensor_type == SENSOR_TYPE_SUCCESS_RATE:
            return "%"

    @property
    def state_class(self):
        if self.sensor_type == SENSOR_TYPE_WATER_FRESHNESS:
            return SensorStateClass.MEASUREMENT
        if self.sensor_type == SENSOR_TYPE_SUCCESS_RATE:
            return SensorStateClass.MEASUREMENT
