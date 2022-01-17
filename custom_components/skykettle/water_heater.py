"""SkyKettle."""
import logging
from homeassistant.components.water_heater import (
    SUPPORT_OPERATION_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    WaterHeaterEntity,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect
from homeassistant.const import *

from .skykettle import SkyKettle
from .const import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities, discovery_info=None):
    """Set up the SkyKettle entry."""
    async_add_entities([SkyWaterHeater(hass, entry)])


class SkyWaterHeater(WaterHeaterEntity):
    """Representation of a SkyKettle water_heater device."""

    def __init__(self, hass, entry):
        """Initialize the water_heater device."""
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
        return self.entry.data.get(CONF_FRIENDLY_NAME, FRIENDLY_NAME)

    @property
    def icon(self):
        return "mdi:kettle"

    @property
    def device_class(self):
        return DOMAIN

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
    def unique_id(self):
        return self.entry.entry_id + "_water_heater"

    @property
    def entity_category(self):
        return None

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def min_temp(self):
        return ROOM_TEMP

    @property
    def max_temp(self):
        return BOIL_TEMP

    @property
    def operation_list(self):
        return [STATE_OFF] + list(SkyKettle.MODE_NAMES.values())
        # return [
        #     STATE_OFF,
        #     SkyKettle.MODE_NAMES[SkyKettle.MODE_BOIL],
        #     SkyKettle.MODE_NAMES[SkyKettle.MODE_BOIL_HEAT],
        #     SkyKettle.MODE_NAMES[SkyKettle.MODE_HEAT]
        # ]            

    @property
    def extra_state_attributes(self):
        sw_version = self.kettle.sw_version
        if sw_version:
            major, minor = sw_version
            sw_version = f"{major}.{minor}"
            updates = {ATTR_SW_VERSION: sw_version}
            self.hass.config_entries.async_update_entry(
                self.entry, data={**self.entry.data, **updates}
            )
        data = {
            "target_temp_step": 5,
            "connected": self.kettle.connected,
            "auth_ok": self.kettle.auth_ok,
            "sw_version": sw_version,
            "success_rate": self.kettle.success_rate,
            "persistent_connection": self.kettle.persistent,
            "poll_interval": self.entry.data.get(CONF_SCAN_INTERVAL, 0),
            "ontime_seconds": self.kettle.ontime.total_seconds(),
            "ontime_string": str(self.kettle.ontime),
            "energy_wh": self.kettle.energy_wh, 
            "heater_on_count": self.kettle.heater_on_count, 
            "user_on_count": self.kettle.user_on_count,
            "sound_enabled": self.kettle.sound_enabled,
            "color_interval": self.kettle.color_interval,
            "boil_time": self.kettle.boil_time,
            "water_hours": self.kettle.water_hours,
            "lamp_auto_off_hours": self.kettle.lamp_auto_off_hours,
            "light_switch_boil": self.kettle.light_switch_boil,
            "light_switch_sync": self.kettle.light_switch_sync,
        }
        return data

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        return self.kettle.target_mode != None

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.kettle.set_target_mode(SkyKettle.MODE_NAMES[SkyKettle.MODE_BOIL])

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.kettle.set_target_mode(None)

    @property
    def current_temperature(self):
        return self.kettle.current_temp
    
    @property
    def target_temperature(self):
        return self.kettle.target_temp

    @property 
    def current_operation(self):
        return self.kettle.target_mode_str

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        target_temperature = kwargs.get(ATTR_TEMPERATURE)        
        await self.kettle.set_target_temp(target_temperature)
        async_dispatcher_send(self.hass, DISPATCHER_UPDATE)

    async def async_set_operation_mode(self, operation_mode):
        """Set new operation mode."""
        await self.kettle.set_target_mode(operation_mode)
        async_dispatcher_send(self.hass, DISPATCHER_UPDATE)
