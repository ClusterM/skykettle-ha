import logging
import pexpect
import asyncio
from time import time, sleep
try:
    from const import *
except ModuleNotFoundError:
    from .const import *
try:
    from skykettle import SkyKettle
except ModuleNotFoundError:
    from .skykettle import SkyKettle
import traceback

_LOGGER = logging.getLogger(__name__)


class KettleConnection(SkyKettle):
    BLE_TIMEOUT = 1.5
    MAX_TRIES = 5
    TRIES_INTERVAL = 0.5
    STATS_INTERVAL = 60
    TARGET_TTL = 60

    def __init__(self, mac, key, persistent=True):
        SkyKettle.__init__(self)
        self._child = None
        self._mac = mac
        self._key = key
        self.persistent = persistent
        self._connected = False
        self._auth_ok = False
        self._iter = 0
        self._connect_lock = asyncio.Lock()
        self._command_lock = asyncio.Lock()
        self._last_set_target = 0
        self._last_get_stats = 0
        self._last_connect_ok = False
        self._last_auth_ok = False
        self._successes = []
        self._target_state = None
        self._status = None
        self._stats = None
        self._lamp_auto_off_hours = None
        self._light_switch_boil = None
        self._light_switch_sync = None
        self._fresh_water = None

        self._disposed = False

    async def command(self, command, params=[]):        
        async with self._command_lock:
            if self._disposed:
                raise DisposedError()
            if not self._connected or not self._child:
                raise IOError("not connected")
            self._iter = (self._iter + 1) % 256
            _LOGGER.debug(f"Writing command {command:02x}, data: [{' '.join([f'{c:02x}' for c in params])}]")
            data = f"char-write-req 0x000e 55{self._iter:02x}{''.join([f'{c:02x}' for c in [command] + list(params)])}aa"
            #_LOGGER.debug(f"Writing {data}")
            self._child.sendline(data)
            while True:
                r = await self._child.expect([
                        r"value:([ 0-9a-f]*)\r\n.*?\[LE\]> ", 
                        r"Disconnected\r\n.*?\[LE\]> ",
                        #r"Invalid file descriptor.\r\n"
                    ], async_=True)
                if r == 1:
                    _LOGGER.debug("'Disconnected' message received")
                    raise IOError("Disconnected")
                # elif r == 2:
                #     _LOGGER.error("'Invalid file descriptor' message received")
                #     _LOGGER.debug(self._child)
                #     #raise IOError("Invalid file descriptor")                
                #     continue
                hex_response = self._child.match.group(1).decode().strip()
                #_LOGGER.debug(f"Received (raw): {hex_response}")
                r = bytes.fromhex(hex_response.replace(' ',''))
                if r[0] != 0x55 or r[-1] != 0xAA:
                    raise IOError("Invalid response magic")
                if r[1] == self._iter: break
            if r[2] != command:
                raise IOError("Invalid response command")
            clean = bytes(r[3:-1])
            _LOGGER.debug(f"Received (clean): {' '.join([f'{c:02x}' for c in clean])}")
            return clean

    async def _connect(self):
        if self._disposed:
            raise DisposedError()
        if self._connected and self._child and self._child.isalive(): return
        if not self._child or not self._child.isalive():
            _LOGGER.debug("Staring gatttool...")
            self._child = pexpect.spawn("gatttool", ['-I', '-t', 'random', '-b', self._mac], timeout=KettleConnection.BLE_TIMEOUT)
            await self._child.expect(r"\[LE\]> ", async_=True)
            _LOGGER.debug("Started gatttool")
        self._child.sendline(f"connect")
        await self._child.expect(r"Attempting to connect.*?\[LE\]> ", async_=True)
        _LOGGER.debug("Attempting to connect...")
        await self._child.expect(r"Connection successful.*?\[LE\]> ", async_=True)
        self._child.sendline("char-write-cmd 0x000c 0100")
        await self._child.expect(r"\[LE\]> ", async_=True)
        _LOGGER.debug("Connected to the Kettle")

    auth = lambda self: super().auth(self._key)

    async def _disconnect(self):
        try:
            if self._child and self._child.isalive():
                self._child.sendline(f"disconnect")
                await self._child.expect(r"\[LE\]> ", async_=True)
                if self._connected:
                    _LOGGER.debug("Disconnected")
        finally:
            self._connected = False
            self._auth_ok = False

    async def _terminate(self):
        try:
            if self._child and self._child.isalive():
                try:
                    self._child.sendcontrol('d')
                    timeout = 1
                    while self._child.isalive():
                        await asyncio.sleep(0.025)
                        timeout = timeout - 0.25
                        if timeout <= 0:
                            self._child.terminate(force=True)
                            break
                    _LOGGER.debug("Terminated")
                except Exception as ex:
                    _LOGGER.error(f"Can't terminate, error ({type(ex).__name__}): {str(ex)}")
        finally:
            self._child = None

    async def disconnect(self):
        async with self._connect_lock:
            try:
                await self._disconnect()
            except:
                pass
            await self._terminate()

    async def _connect_if_need(self):
        async with self._connect_lock:
            if not self._connected or not self._child or not self._child.isalive():
                try:
                    await self._connect()
                    self._last_connect_ok = self._connected = True
                except Exception as ex:
                    self._last_connect_ok = False
                    raise ex
            if not self._auth_ok:
                self._last_auth_ok = self._auth_ok = await self.auth()
                if not self._auth_ok:
                    _LOGGER.warning(f"Auth failed. You need to enable pairing mode on the kettle.")
                    raise AuthError("Auth failed")
                _LOGGER.debug("Auth ok")
                await self.sync_time()
                self._sw_version = await self.get_version()

    async def _disconnect_if_need(self):
        if not self.persistent:
            await self.disconnect()
    
    async def update(self, tries=None):
        try:
            if self._disposed: return
            if tries == None: tries = KettleConnection.MAX_TRIES
            _LOGGER.debug(f"Updating")
            await self._connect_if_need()

            self._status = await self.get_status()

            if self._target_state != None:
                _LOGGER.debug(f"Target state: {self._target_state}")
                target_mode, target_temp = self._target_state
                if target_mode in [SkyKettle.MODE_BOIL_HEAT, SkyKettle.MODE_HEAT] and target_temp < SkyKettle.MIN_TEMP:
                    target_mode = None
                if target_mode == None and self._status.is_on:
                    _LOGGER.info("Need to turn off the kettle")
                    await self.turn_off()
                    await asyncio.sleep(0.2)
                    self._status = await self.get_status()
                elif target_mode != None and not self._status.is_on:
                    _LOGGER.info("Need to set mode and turn on the kettle")
                    await self.set_main_mode(target_mode, target_temp, self._status.boil_time)
                    await self.turn_on()
                    await asyncio.sleep(0.2)
                    self._status = await self.get_status()
                elif target_mode != None  and (
                        target_mode != self._status.mode or
                        (target_mode in [SkyKettle.MODE_HEAT, SkyKettle.MODE_BOIL_HEAT] and 
                         target_temp != self._status.target_temp)):
                    _LOGGER.info("Need to switch mode of the kettle and restart it")
                    await self.turn_off()
                    await self.set_main_mode(target_mode, target_temp, self._status.boil_time)
                    await self.turn_on()
                    await asyncio.sleep(0.2)
                    self._status = await self.get_status()
                self._target_state = None

            if self._last_get_stats + KettleConnection.STATS_INTERVAL < time():
                self._last_get_stats = time()
                # Not sure that every kettle/firmware supports this, so ignoring exceptions
                try:
                    self._stats = await self.get_stats()
                except Exception as ex:
                    _LOGGER.debug(f"Can't get stats ({type(ex).__name__}): {str(ex)}")
                    pass
                try:
                    self._light_switch_boil = await self.get_light_switch(SkyKettle.LIGHT_BOIL)
                    self._light_switch_sync = await self.get_light_switch(SkyKettle.LIGHT_SYNC)                    
                except Exception as ex:
                    _LOGGER.debug(f"Can't get light switches ({type(ex).__name__}): {str(ex)}")
                try:
                    self._lamp_auto_off_hours = await self.get_lamp_auto_off_hours()
                except Exception as ex:
                    _LOGGER.debug(f"Can't get lamp auto off hours ({type(ex).__name__}): {str(ex)}")
                try:
                    self._fresh_water = await self.get_fresh_water()
                except Exception as ex:
                    _LOGGER.debug(f"Can't get fresh water info ({type(ex).__name__}): {str(ex)}")

            await self._disconnect_if_need()
            self._successes.append(True)

        except Exception as ex:
            if type(ex) == DisposedError: return
            await self.disconnect()
            if self._target_state != None and self._last_set_target + KettleConnection.TARGET_TTL < time():
                _LOGGER.warning(f"Can't set mode to {self._target_state} for {KettleConnection.TARGET_TTL} seconds, stop trying")
                self._target_state = None
            if type(ex) == AuthError: return
            self._successes.append(False)
            if type(ex) == pexpect.exceptions.TIMEOUT:
                msg = "Timeout" # too many debug info
            else:
                msg = f"{type(ex).__name__}: {str(ex)}"
            if tries > 1: 
                _LOGGER.info(f"{msg}, retry #{KettleConnection.MAX_TRIES - tries + 1}")
                await asyncio.sleep(KettleConnection.TRIES_INTERVAL)
                await self.update(tries=tries-1)
            elif type(ex) != pexpect.exceptions.TIMEOUT:
                _LOGGER.error(f"{traceback.format_exc()}")
            else:
                _LOGGER.info(f"Timeout")
                #_LOGGER.warning(f"{type(ex).__name__}: {str(ex)}")
        
        if len(self._successes) > 100: self._successes = self._successes[-100:]

    @property
    def success_rate(self):
        if len(self._successes) == 0: return 0
        return int(100 * len([s for s in self._successes if s]) / len(self._successes))

    async def _set_target_state(self, target_mode, target_temp = 0):
        self._target_state = target_mode, target_temp
        self._last_set_target = time()
        await self.update()

    async def cancel_target(self):
        self._target_state = None

    def stop(self):
        if self._disposed: return
        self._disposed = True
        if self._child and self._child.isalive():
            self._child.sendcontrol('d')
            timeout = 1
            while self._child.isalive():
                sleep(0.025)
                timeout = timeout - 0.25
                if timeout <= 0:
                    self._child.terminate(force=True)
                    break
            self._child = None
        self._connected = False
        _LOGGER.info("Disposed.")

    def __del__(self):
        self.stop()
    
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
            if target_mode == None:
                return ROOM_TEMP
        else:
            if self._status:
                if not self._status.is_on: 
                    return ROOM_TEMP
                if self._status.mode in [SkyKettle.MODE_BOIL_HEAT, SkyKettle.MODE_HEAT]:
                    return self._status.target_temp
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

    async def set_target_temp(self, target_temp):
        _LOGGER.info(f"Setting target temperature to {target_temp}")
        target_mode = self.current_mode
        if target_mode == None and target_temp >= BOIL_TEMP:
            # If set to 100 - just boiling
            target_mode = SkyKettle.MODE_BOIL
        elif target_mode == None and target_temp >= SkyKettle.MIN_TEMP:
            # Kittle is off now, need to turn on some mode
            target_mode = SkyKettle.MODE_HEAT # or BOIL_HEAT?
        elif target_mode == SkyKettle.MODE_BOIL_HEAT and target_temp < SkyKettle.MIN_TEMP:
            # Disable heating after boiling
            target_mode = SkyKettle.MODE_BOIL
        if target_mode != self.current_mode:
            _LOGGER.info(f"Mode autoswitched to {target_mode}")
        await self._set_target_state(target_mode, target_temp)

    async def set_target_mode(self, operation_mode):
        """Set new operation mode."""
        _LOGGER.info(f"Setting target mode to {operation_mode}")
        target_temp = self.target_temp
        target_mode = None
        # Get target mode ID
        vs = [k for k, v in SkyKettle.MODE_NAMES.items() if v == operation_mode]
        if len(vs) > 0: target_mode = vs[0]
        # Need to set at least MIN_TEMP when heating enabled
        if target_mode in [SkyKettle.MODE_HEAT, SkyKettle.MODE_BOIL_HEAT] and target_temp < SkyKettle.MIN_TEMP:
            target_temp = SkyKettle.MIN_TEMP
        if target_temp != self.target_temp:
            _LOGGER.info(f"Target temperature autoswitched to {target_temp}")
        await self._set_target_state(target_mode, target_temp)

    @property
    def connected(self):
        return self._connected

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
    def water_hours(self):
        if not self._fresh_water: return None
        return self._fresh_water.water_hours

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

class AuthError(Exception):
    pass

class DisposedError(Exception):
    pass