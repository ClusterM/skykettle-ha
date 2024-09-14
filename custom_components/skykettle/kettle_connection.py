import asyncio
import logging
import traceback
from time import monotonic

from bleak import BleakClient

from homeassistant.components import bluetooth

from .const import *
from .skykettle import SkyKettle

_LOGGER = logging.getLogger(__name__)


class KettleConnection(SkyKettle):
    UUID_SERVICE = "6e400001-b5a3-f393e-0a9e-50e24dcca9e"
    UUID_TX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
    UUID_RX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
    CONNECTION_TIMEOUT = 10
    BLE_RECV_TIMEOUT = 1.5
    MAX_TRIES = 3
    TRIES_INTERVAL = 0.5
    STATS_INTERVAL = 15
    TARGET_TTL = 30

    def __init__(self, mac, key, persistent=True, adapter=None, hass=None, model=None):
        super().__init__(model)
        self._device = None
        self._client = None
        self._mac = mac
        self._key = key
        self.persistent = persistent
        self.adapter = adapter
        self.hass = hass
        self._auth_ok = False
        self._sw_version = None
        self._iter = 0
        self._update_lock = asyncio.Lock()
        self._last_set_target = 0
        self._last_get_stats = 0
        self._last_connect_ok = False
        self._last_auth_ok = False
        self._successes = []
        self._target_state = None
        self._target_boil_time = None
        self._status = None
        self._stats = None
        self._lamp_auto_off_hours = None
        self._light_switch_boil = None
        self._light_switch_sync = None
        self._fresh_water = None
        self._colors = {}
        self._disposed = False
        self._last_data = None

    async def command(self, command, params=[]):
        if self._disposed:
            raise DisposedError()
        if not self._client or not self._client.is_connected:
            raise IOError("not connected")
        self._iter = (self._iter + 1) % 256
        _LOGGER.debug(f"Writing command {command:02x}, data: [{' '.join([f'{c:02x}' for c in params])}]")
        data = bytes([0x55, self._iter, command] + list(params) + [0xAA])
        # _LOGGER.debug(f"Writing {data}")
        self._last_data = None
        await self._client.write_gatt_char(KettleConnection.UUID_TX, data)
        timeout_time = monotonic() + KettleConnection.BLE_RECV_TIMEOUT
        while True:
            await asyncio.sleep(0.05)
            if self._last_data:
                r = self._last_data
                if r[0] != 0x55 or r[-1] != 0xAA:
                    raise IOError("Invalid response magic")
                if r[1] == self._iter:
                    break
                else:
                    self._last_data = None
            if monotonic() >= timeout_time: raise IOError("Receive timeout")
        if r[2] != command:
            raise IOError("Invalid response command")
        clean = bytes(r[3:-1])
        _LOGGER.debug(f"Received: {' '.join([f'{c:02x}' for c in clean])}")
        return clean

    def _rx_callback(self, sender, data):
        # _LOGGER.debug(f"Received (full): {' '.join([f'{c:02x}' for c in data])}")
        self._last_data = data

    async def _connect(self):
        if self._disposed:
            raise DisposedError()
        if self._client and self._client.is_connected: return
        self._device = bluetooth.async_ble_device_from_address(self.hass, self._mac)
        self._client = BleakClient(self._device)
        _LOGGER.debug("Connecting to the Kettle...")
        await asyncio.wait_for(
            # Bluez connection timeout is not working actually
            self._client.connect(timeout=KettleConnection.CONNECTION_TIMEOUT),
            timeout=KettleConnection.CONNECTION_TIMEOUT
        )
        _LOGGER.debug("Connected to the Kettle")
        await self._client.start_notify(KettleConnection.UUID_RX, self._rx_callback)
        _LOGGER.debug("Subscribed to RX")

    auth = lambda self: super().auth(self._key)

    async def _disconnect(self):
        try:
            if self._client:
                was_connected = self._client.is_connected
                await self._client.disconnect()
                if was_connected: _LOGGER.debug("Disconnected")
        finally:
            self._auth_ok = False
            self._device = None
            self._client = None

    async def disconnect(self):
        try:
            await self._disconnect()
        except:
            pass

    async def _connect_if_need(self):
        if self._client and not self._client.is_connected:
            _LOGGER.debug("Connection lost")
            await self.disconnect()
        if not self._client or not self._client.is_connected:
            try:
                await self._connect()
                self._last_connect_ok = True
            except Exception as ex:
                await self.disconnect()
                self._last_connect_ok = False
                raise ex
        if not self._auth_ok:
            self._last_auth_ok = self._auth_ok = await self.auth()
            if not self._auth_ok:
                _LOGGER.error(f"Auth failed. You need to enable pairing mode on the kettle.")
                raise AuthError("Auth failed")
            _LOGGER.debug("Auth ok")
            self._sw_version = await self.get_version()
            await self.sync_time()

    async def _disconnect_if_need(self):
        if not self.persistent and self.target_mode != SkyKettle.MODE_GAME:
            await self.disconnect()

    async def update(self, tries=MAX_TRIES, force_stats=False, extra_action=None, commit=False):
        try:
            async with self._update_lock:
                if self._disposed: return
                _LOGGER.debug(f"Updating")
                if not self.available: force_stats = True # Update stats after unavailable state
                await self._connect_if_need()

                if extra_action: await extra_action

                # Is there scheduled boil_time?
                self._status = await self.get_status()
                boil_time = self._status.boil_time
                if self._target_boil_time != None and self._target_boil_time != boil_time:
                    try:
                        _LOGGER.debug(f"Need to update boil time from {boil_time} to {self._target_boil_time}")
                        boil_time = self._target_boil_time
                        if self._target_state == None: # To return previous state
                            self._target_state = self._status.mode if self._status.is_on else None, self._status.target_temp
                            self._last_set_target = monotonic()
                        if self._status.is_on:
                            await self.turn_off()
                            await asyncio.sleep(0.2)
                        await self.set_main_mode(self._status.mode, self._status.target_temp, boil_time)
                        _LOGGER.info(f"Boil time is succesfully set to {boil_time}")
                    except Exception as ex:
                        _LOGGER.error(f"Can't update boil time ({type(ex).__name__}): {str(ex)}")
                    self._status = await self.get_status()
                self._target_boil_time = None

                if commit: await self.commit()

                # If there is scheduled state
                if self._target_state != None:
                    target_mode, target_temp = self._target_state
                    # How to set mode?
                    if target_mode == None and self._status.is_on:
                        _LOGGER.info(f"State: {self._status} -> {self._target_state}")
                        _LOGGER.info("Need to turn off the kettle...")
                        await self.turn_off()
                        _LOGGER.info("The kettle was turned off")
                        await asyncio.sleep(0.2)
                        self._status = await self.get_status()
                    elif target_mode != None and not self._status.is_on:
                        _LOGGER.info(f"State: {self._status} -> {self._target_state}")
                        _LOGGER.info("Need to set mode and turn on the kettle...")
                        await self.set_main_mode(target_mode, target_temp, boil_time)
                        _LOGGER.info("New mode was set")
                        await self.turn_on()
                        _LOGGER.info("The kettle was turned on")
                        await asyncio.sleep(0.2)
                        self._status = await self.get_status()
                    elif target_mode != None  and (
                            target_mode != self._status.mode or
                            (target_mode in [SkyKettle.MODE_HEAT, SkyKettle.MODE_BOIL_HEAT] and
                            target_temp != self._status.target_temp)):
                        _LOGGER.info(f"State: {self._status} -> {self._target_state}")
                        _LOGGER.info("Need to switch mode of the kettle and restart it")
                        await self.turn_off()
                        _LOGGER.info("The kettle was turned off")
                        await asyncio.sleep(0.2)
                        await self.set_main_mode(target_mode, target_temp, boil_time)
                        _LOGGER.info("New mode was set")
                        await self.turn_on()
                        _LOGGER.info("The kettle was turned on")
                        await asyncio.sleep(0.2)
                        self._status = await self.get_status()
                    else:
                        _LOGGER.debug(f"There is no reason to update state")
                    # Not scheduled anymore
                    self._target_state = None

                if self._last_get_stats + KettleConnection.STATS_INTERVAL < monotonic() or force_stats:
                    self._last_get_stats = monotonic()
                    self._stats = await self.get_stats()
                    self._light_switch_boil = await self.get_light_switch(SkyKettle.LIGHT_BOIL)
                    self._light_switch_sync = await self.get_light_switch(SkyKettle.LIGHT_SYNC)
                    self._lamp_auto_off_hours = await self.get_lamp_auto_off_hours()
                    self._fresh_water = await self.get_fresh_water()
                    for lt in [SkyKettle.LIGHT_BOIL, SkyKettle.LIGHT_LAMP]:
                        self._colors[lt] = await self.get_colors(lt)

                await self._disconnect_if_need()
                self.add_stat(True)
                return True

        except Exception as ex:
            await self.disconnect()
            if self._target_state != None and self._last_set_target + KettleConnection.TARGET_TTL < monotonic():
                _LOGGER.warning(f"Can't set mode to {self._target_state} for {KettleConnection.TARGET_TTL} seconds, stop trying")
                self._target_state = None
            if type(ex) == AuthError: return
            self.add_stat(False)
            if tries > 1 and extra_action == None:
                _LOGGER.debug(f"{type(ex).__name__}: {str(ex)}, retry #{KettleConnection.MAX_TRIES - tries + 1}")
                await asyncio.sleep(KettleConnection.TRIES_INTERVAL)
                return await self.update(tries=tries-1, force_stats=force_stats, extra_action=extra_action, commit=commit)
            else:
                _LOGGER.warning(f"Can't update status, {type(ex).__name__}: {str(ex)}")
                _LOGGER.debug(traceback.format_exc())
            return False

    def add_stat(self, value):
        self._successes.append(value)
        if len(self._successes) > 100: self._successes = self._successes[-100:]

    @staticmethod
    def limit_temp(temp):
        if temp != None and temp > SkyKettle.MAX_TEMP:
            return SkyKettle.MAX_TEMP
        elif temp != None and temp < SkyKettle.MIN_TEMP:
            return SkyKettle.MIN_TEMP
        else:
            return temp

    @staticmethod
    def get_mode_name(mode_id):
        if mode_id == None: return "off"
        return SkyKettle.MODE_NAMES[mode_id]

    @property
    def success_rate(self):
        if len(self._successes) == 0: return 0
        return int(100 * len([s for s in self._successes if s]) / len(self._successes))

    async def _set_target_state(self, target_mode, target_temp = 0):
        self._target_state = target_mode, target_temp
        self._last_set_target = monotonic()
        await self.update()

    async def cancel_target(self):
        self._target_state = None

    def stop(self):
        if self._disposed: return
        self._disconnect()
        self._disposed = True
        _LOGGER.info("Stopped.")

    @property
    def available(self):
        return self._last_connect_ok and self._last_auth_ok

    @property
    def current_temp(self):
        if self._status:
            return self._status.current_temp
        return None

    @property
    def current_mode(self):
        if self._status and self._status.is_on:
            return self._status.mode
        return None

    @property
    def target_temp(self):
        if self._target_state:
            target_mode, target_temp = self._target_state
            if target_mode in [SkyKettle.MODE_BOIL_HEAT, SkyKettle.MODE_HEAT]:
                return target_temp
            if target_mode == SkyKettle.MODE_BOIL:
                return BOIL_TEMP
            if target_mode == None:
                return ROOM_TEMP
        if self._status:
            if self._status.is_on:
                if self._status.mode in [SkyKettle.MODE_BOIL_HEAT, SkyKettle.MODE_HEAT]:
                    return self._status.target_temp
                if self._status.mode == SkyKettle.MODE_BOIL:
                    return BOIL_TEMP
            else: # Off
                return ROOM_TEMP
        return None

    @property
    def target_mode(self):
        if self._target_state:
            target_mode, target_temp = self._target_state
            return target_mode
        else:
            if self._status and self._status.is_on:
                return self._status.mode
        return None

    @property
    def target_mode_str(self):
        return self.get_mode_name(self.target_mode)

    async def set_target_temp(self, target_temp, operation_mode = None):
        """Set new temperature."""
        if target_temp == self.target_temp: return # already set
        _LOGGER.info(f"Setting target temperature to {target_temp}")
        target_mode = self.target_mode
        vs = [k for k, v in SkyKettle.MODE_NAMES.items() if v == operation_mode]
        if len(vs) > 0: target_mode = vs[0]
        # Some checks for mode
        if target_temp < SkyKettle.MIN_TEMP:
            # Just turn off
            target_mode = None
        elif target_temp > SkyKettle.MAX_TEMP:
            # If set to ~100 - just boiling
            target_mode = SkyKettle.MODE_BOIL # or BOIL_HEAT?
        elif target_mode == None:
            # Kittle is off now, need to turn on some mode
            target_mode = SkyKettle.MODE_HEAT # or BOIL_HEAT?
        elif target_mode == SkyKettle.MODE_BOIL:
            # Replace boiling with...
            target_mode = SkyKettle.MODE_HEAT # or BOIL_HEAT?
        if target_mode != self.current_mode:
            _LOGGER.info(f"Mode autoswitched to {target_mode} ({self.get_mode_name(target_mode)})")
        await self._set_target_state(target_mode, target_temp)

    async def set_target_mode(self, operation_mode):
        """Set new operation mode."""
        if operation_mode == self.target_mode_str: return # already set
        _LOGGER.info(f"Setting target mode to {operation_mode}")
        target_mode = None
        # Get target mode ID
        vs = [k for k, v in SkyKettle.MODE_NAMES.items() if v == operation_mode]
        if len(vs) > 0: target_mode = vs[0]
        # Set heating temperature if not set
        target_temp = self.target_temp
        # Some checks for temperature
        if target_mode in [SkyKettle.MODE_BOIL]:
            target_temp = 0
        elif target_mode in [SkyKettle.MODE_LAMP, SkyKettle.MODE_GAME]:
            target_temp = 85
        elif target_temp == None:
            target_temp = SkyKettle.MAX_TEMP
        else:
            target_temp = self.limit_temp(target_temp)
        if target_temp != self.target_temp:
            _LOGGER.info(f"Target temperature autoswitched to {target_temp}")
        await self._set_target_state(target_mode, target_temp)

    @property
    def connected(self):
        return True if self._client and self._client.is_connected else False

    @property
    def auth_ok(self):
        return self._auth_ok

    @property
    def sw_version(self):
        return self._sw_version

    @property
    def sound_enabled(self):
        if not self._status: return None
        return self._status.sound_enabled

    @property
    def color_interval(self):
        if not self._status: return None
        return self._status.color_interval

    @property
    def boil_time(self):
        if not self._status: return None
        return self._status.boil_time

    @property
    def lamp_auto_off_hours(self):
        return self._lamp_auto_off_hours

    @property
    def light_switch_boil(self):
        return self._light_switch_boil

    @property
    def light_switch_sync(self):
        return self._light_switch_sync

    @property
    def colors_boil(self):
        return self._colors.get(SkyKettle.LIGHT_BOIL, None)

    @property
    def colors_lamp(self):
        return self._colors.get(SkyKettle.LIGHT_LAMP, None)

    @property
    def parental_control(self):
        if not self._status: return None
        return self._status.parental_control

    @property
    def error_code(self):
        if not self._status: return None
        return self._status.error_code

    def get_color(self, light_type, n):
        if light_type not in self._colors: return None
        colors = self._colors[light_type]
        if n == 0: return colors.r_low, colors.g_low, colors.b_low
        if n == 1: return colors.r_mid, colors.g_mid, colors.b_mid
        if n == 2: return colors.r_high, colors.g_high, colors.b_high

    def get_brightness(self, light_type):
        if light_type not in self._colors: return None
        colors = self._colors[light_type]
        return colors.brightness

    def get_temperature(self, light_type, n):
        if light_type not in self._colors: return None
        colors = self._colors[light_type]
        if n == 0: return colors.temp_low
        if n == 1: return colors.temp_mid
        if n == 2: return colors.temp_high

    @property
    def water_freshness_hours(self):
        if not self._fresh_water: return None
        return self._fresh_water.water_freshness_hours

    @property
    def ontime(self):
        if not self._stats: return None
        return self._stats.ontime

    @property
    def energy_wh(self):
        if not self._stats: return None
        return self._stats.energy_wh

    @property
    def heater_on_count(self):
        if not self._stats: return None
        return self._stats.heater_on_count

    @property
    def user_on_count(self):
        if not self._stats: return None
        return self._stats.user_on_count

    async def set_boil_time(self, value):
        value = int(value)
        _LOGGER.info(f"Setting boil time to {value}")
        self._target_boil_time = value
        await self.update(commit=True)

    async def impulse_color(self, r, g, b, brightness):
        await self.update(extra_action=super().impulse_color(r, g, b, brightness))

    async def set_sound(self, value):
        if await self.update(force_stats=False, extra_action=super().set_sound(value), commit=True):
            _LOGGER.info(f"Sound is set to {value}")
        else:
            _LOGGER.error(f"Can't set sound to {value}")

    async def set_light_switch(self, light_type, value):
        if await self.update(force_stats=True, extra_action=super().set_light_switch(light_type, value), commit=True):
            _LOGGER.info(f"Light 0x{light_type:02X} is set to {value}")
        else:
            _LOGGER.error(f"Can't set light 0x{light_type:02X} to {value}")

    async def set_color(self, light_type, n, color):
        if light_type not in self._colors: return
        self._last_get_stats = monotonic() # To avoid race condition
        colors = self._colors[light_type]
        r, g, b = color
        if n == 0: colors = colors._replace(r_low=int(r), g_low=int(g), b_low=int(b))
        if n == 1: colors = colors._replace(r_mid=int(r), g_mid=int(g), b_mid=int(b))
        if n == 2: colors = colors._replace(r_high=int(r), g_high=int(g), b_high=int(b))
        self._colors[light_type] = colors
        if await self.update(extra_action=super().set_colors(colors), commit=True):
            _LOGGER.info(f"Color 0x{light_type:02X}/{n} is set to {color}")
        else:
            _LOGGER.error(f"Can't set color 0x{light_type:02X}/{n} to {color}")

    async def set_brightness(self, light_type, brightness):
        brightness = int(brightness)
        if light_type not in self._colors: return
        self._last_get_stats = monotonic() # To avoid race condition
        colors = self._colors[light_type]
        colors = colors._replace(brightness=brightness, unknown1=brightness, unknown2=brightness)
        self._colors[light_type] = colors
        if await self.update(extra_action=super().set_colors(colors), commit=True):
            _LOGGER.info(f"Color 0x{light_type:02X} brightness is set to {brightness}")
        else:
            _LOGGER.error(f"Can't set color 0x{light_type:02X} brightness to {brightness}")

    async def set_temperature(self, light_type, n, temp):
        temp = int(temp)
        if light_type not in self._colors: return
        self._last_get_stats = monotonic() # To avoid race condition
        colors = self._colors[light_type]
        temp = int(temp)
        if n == 0: colors = colors._replace(temp_low=temp)
        if n == 1: colors = colors._replace(temp_mid=temp)
        if n == 2: colors = colors._replace(temp_high=temp)
        self._colors[light_type] = colors
        if await self.update(extra_action=super().set_colors(colors), commit=True):
            _LOGGER.info(f"Color 0x{light_type:02X}/{n} temperature is set to {temp}")
        else:
            _LOGGER.error(f"Can't set color 0x{light_type:02X}/{n} temperature to {temp}")

    async def set_lamp_color_interval(self, secs):
        secs = int(secs)
        self._last_get_stats = monotonic() # To avoid race condition
        if self._status: self._status._replace(color_interval=secs)
        if await self.update(extra_action=super().set_lamp_color_interval(secs), commit=True):
            _LOGGER.info(f"Lamp color interval is set to {secs}")
        else:
            _LOGGER.error(f"Can't set lamp color interval to {secs}")

    async def set_lamp_auto_off_hours(self, hours):
        hours = int(hours)
        self._last_get_stats = monotonic() # To avoid race condition
        self._lamp_auto_off_hours = hours
        if await self.update(extra_action=super().set_lamp_auto_off_hours(hours)):
            _LOGGER.info(f"Lamp auto off hours is set to {hours}")
        else:
            _LOGGER.error(f"Can't set lamp auto off hours to {hours}")


class AuthError(Exception):
    pass

class DisposedError(Exception):
    pass
