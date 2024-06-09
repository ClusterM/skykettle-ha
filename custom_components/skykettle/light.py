"""SkyKettle."""
import logging

from homeassistant.components.light import (ATTR_BRIGHTNESS, ATTR_RGB_COLOR,
                                            ColorMode, LightEntity, LightEntityFeature)
from homeassistant.const import CONF_FRIENDLY_NAME, STATE_OFF
from homeassistant.helpers.dispatcher import (async_dispatcher_connect,
                                              dispatcher_send)
from homeassistant.helpers.entity import EntityCategory

from .const import *
from .skykettle import SkyKettle

_LOGGER = logging.getLogger(__name__)


LIGHT_GAME = "light"


async def async_setup_entry(hass, entry, async_add_entities, discovery_info=None):
    """Set up the SkyKettle entry."""
    model_code = hass.data[DOMAIN][entry.entry_id][DATA_CONNECTION].model_code
    if model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
        async_add_entities([
            KettleLight(hass, entry, LIGHT_GAME),
            KettleLight(hass, entry, SkyKettle.LIGHT_BOIL, 0),
            KettleLight(hass, entry, SkyKettle.LIGHT_BOIL, 1),
            KettleLight(hass, entry, SkyKettle.LIGHT_BOIL, 2),
            KettleLight(hass, entry, SkyKettle.LIGHT_LAMP, 0),
            KettleLight(hass, entry, SkyKettle.LIGHT_LAMP, 1),
            KettleLight(hass, entry, SkyKettle.LIGHT_LAMP, 2),
        ])


class KettleLight(LightEntity):
    """Representation of a SkyKettle light device."""

    def __init__(self, hass, entry, light_type, n = 0):
        """Initialize the light device."""
        self.hass = hass
        self.entry = entry
        self.light_type = light_type
        self.n = n
        self.on = False
        self.current = (0xFF, 0xFF, 0xFF, 0xFF)

    async def async_added_to_hass(self):
        self.update()
        self.async_on_remove(async_dispatcher_connect(self.hass, DISPATCHER_UPDATE, self.update))

    def update(self):
        self.schedule_update_ha_state()
        if self.light_type == LIGHT_GAME:
            if (self.kettle.target_mode == SkyKettle.MODE_GAME and
                self.kettle.current_mode == SkyKettle.MODE_GAME):
                if not self.on:
                    self.hass.create_task(self.async_turn_on())
            else:
                self.on = False

    @property
    def kettle(self):
        return self.hass.data[DOMAIN][self.entry.entry_id][DATA_CONNECTION]

    @property
    def unique_id(self):
        if self.light_type == LIGHT_GAME:
            return f"{self.entry.entry_id}_{self.light_type}"
        else:
            return f"{self.entry.entry_id}_{self.light_type}_{self.n+1}"

    @property
    def name(self):
        """Name of the entity."""
        if self.light_type == LIGHT_GAME:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + " light"
        if self.light_type == SkyKettle.LIGHT_BOIL:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + f" temperature #{self.n+1} color"
        if self.light_type == SkyKettle.LIGHT_LAMP:
            return (FRIENDLY_NAME + " " + self.entry.data.get(CONF_FRIENDLY_NAME, "")).strip() + f" lamp #{self.n+1} color"

    @property
    def icon(self):
        if self.light_type == LIGHT_GAME:
            return None
        if self.light_type == SkyKettle.LIGHT_LAMP:
            return None
        if self.light_type == SkyKettle.LIGHT_BOIL:
            if self.n == 0:
                return "mdi:thermometer-low"
            if self.n == 1:        
                return "mdi:thermometer"        
            if self.n == 2:
                return "mdi:thermometer-high"

    @property
    def device_info(self):
        return self.hass.data[DOMAIN][DATA_DEVICE_INFO]()

    @property
    def entity_category(self):
        return None

    @property
    def should_poll(self):
        return False

    @property
    def assumed_state(self):
        return False

    @property
    def available(self):
        if self.light_type == LIGHT_GAME:
            return self.kettle.available
        else:
            return self.kettle.available and self.kettle.get_color(self.light_type, self.n) != None

    @property
    def entity_category(self):
        if self.light_type == LIGHT_GAME:
            return None
        else:
            return EntityCategory.CONFIG

    @property
    def rgb_color(self):
        """Return the rgb color value."""
        if self.light_type == LIGHT_GAME:
            r, g, b, brightness = self.current
            return r, g, b
        else:
            return self.kettle.get_color(self.light_type, self.n)

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        if self.light_type == LIGHT_GAME:
            r, g, b, brightness = self.current
            return brightness
        else:
            return self.kettle.get_brightness(self.light_type)

    @property
    def is_on(self):
        """Return true if light is on."""
        if self.light_type == LIGHT_GAME:
            return self.on and self.kettle.target_mode == SkyKettle.MODE_GAME
        else:
            return True # Always on for other modes

    @property
    def supported_features(self):
        """Flag supported features."""
        return LightEntityFeature(0)

    @property
    def color_mode(self):
        """Return the color mode of the light."""
        return ColorMode.RGB

    @property
    def supported_color_modes(self):
        """Flag supported color modes."""
        return {ColorMode.RGB}

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        _LOGGER.debug(f"Turn on ({self.light_type}): {kwargs}")
        if self.light_type == LIGHT_GAME:
            r, g, b, brightness = self.current
            if ATTR_RGB_COLOR in kwargs:
                r, g, b = kwargs[ATTR_RGB_COLOR]
            if ATTR_BRIGHTNESS in kwargs:
                brightness = kwargs[ATTR_BRIGHTNESS]
            _LOGGER.debug(f"Setting {self.light_type} color of the Kettle: r={r}, g={g}, b={b}, brightness={brightness}")
            await self.kettle.set_target_mode(SkyKettle.MODE_NAMES[SkyKettle.MODE_GAME])
            await self.kettle.impulse_color(r, g, b, brightness)
            self.on = True
            self.current = r, g, b, brightness
        else:
            if ATTR_RGB_COLOR in kwargs:
                await self.kettle.set_color(self.light_type, self.n, kwargs[ATTR_RGB_COLOR])
            if ATTR_BRIGHTNESS in kwargs:
                await self.kettle.set_brightness(self.light_type, kwargs[ATTR_BRIGHTNESS])
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        _LOGGER.debug(f"Turn off ({self.light_type}): {kwargs}")
        if self.light_type == LIGHT_GAME:
            await self.kettle.set_target_mode(STATE_OFF)
            self.on = False
        self.hass.async_add_executor_job(dispatcher_send, self.hass, DISPATCHER_UPDATE)
