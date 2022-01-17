"""SkyKettle."""
import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    COLOR_MODE_RGB,
    LightEntity,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect
from homeassistant.const import *

from .skykettle import SkyKettle
from .const import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities, discovery_info=None):
    """Set up the SkyKettle entry."""
    async_add_entities([KettleLight(hass, entry)])


class KettleLight(LightEntity):
    """Representation of a SkyKettle light device."""

    def __init__(self, hass, entry):
        """Initialize the light device."""
        self.hass = hass
        self.entry = entry
        self.on = False
        self.current = (0xFF, 0xFF, 0xFF, 0xFF)

    async def async_added_to_hass(self):
        self.update()
        self.async_on_remove(async_dispatcher_connect(self.hass, DISPATCHER_UPDATE, self.update))

    def update(self):
        self.schedule_update_ha_state()
        if self.kettle.target_mode == SkyKettle.MODE_GAME and self.kettle.current_mode == SkyKettle.MODE_GAME and not self.on:
            self.hass.async_create_task(
                self.async_turn_on()
            )

    @property
    def kettle(self):
        return self.hass.data[DOMAIN][self.entry.entry_id][DATA_CONNECTION]

    @property
    def name(self):
        """Name of the entity."""
        return FRIENDLY_NAME + " light"

    @property
    def device_info(self):
        return self.hass.data[DOMAIN][DATA_DEVICE_INFO]()

    @property
    def icon(self):
        return "mdi:kettle"

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
        return self.kettle.available
    
    @property
    def unique_id(self):
        return self.entry.entry_id + "_light"

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        r, g, b, brightness = self.current
        return brightness

    @property
    def rgb_color(self):
        """Return the rgb color value."""
        r, g, b, brightness = self.current
        return r, g, b

    @property
    def is_on(self):
        """Return true if light is on."""
        return self.on and self.kettle.target_mode == SkyKettle.MODE_GAME

    @property
    def supported_features(self):
        """Flag supported features."""
        return 0

    @property
    def color_mode(self):
        """Return the color mode of the light."""
        return COLOR_MODE_RGB

    @property
    def supported_color_modes(self):
        """Flag supported color modes."""
        return {COLOR_MODE_RGB}

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        _LOGGER.debug(f"Turn on: {kwargs}")
        r, g, b, brightness = self.current
        if ATTR_RGB_COLOR in kwargs:
            r, g, b = kwargs[ATTR_RGB_COLOR]
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
        _LOGGER.debug(f"Setting color of the Kettle: r={r}, g={g}, b={b}, brightness={brightness}")
        await self.kettle.set_target_mode(SkyKettle.MODE_NAMES[SkyKettle.MODE_GAME])
        await self.kettle.impulse_color(r, g, b, brightness)
        self.on = True
        self.current = r, g, b, brightness
        async_dispatcher_send(self.hass, DISPATCHER_UPDATE)

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        _LOGGER.debug(f"Turn off: {kwargs}")
        await self.kettle.set_target_mode(STATE_OFF)
        self.on = False
        async_dispatcher_send(self.hass, DISPATCHER_UPDATE)
