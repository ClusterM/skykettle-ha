import logging
from struct import pack, unpack
from collections import namedtuple
import time
from datetime import datetime, timedelta
import calendar
from abc import abstractmethod

_LOGGER = logging.getLogger(__name__)

class SkyKettle():
    MODE_BOIL = 0x00
    MODE_HEAT = 0x01
    MODE_BOIL_HEAT = 0x02
    MODE_LAMP = 0x03
    MODE_GAME = 0x04
    MODE_NAMES = {
        MODE_BOIL: "Boil",
        MODE_HEAT: "Heat",
        MODE_BOIL_HEAT: "Boil+Heat",
        MODE_LAMP: "Lamp",
        MODE_GAME: "Light"
    }

    LIGHT_BOIL = 0x00
    LIGHT_LAMP = 0x01
    LIGHT_SYNC = 0xC8
    LIGHT_NAMES = {
        LIGHT_BOIL: "boiling_light",
        LIGHT_LAMP: "lamp_light",
        LIGHT_SYNC: "sync_light"
    }

    MAX_TEMP = 90
    MIN_TEMP = 35

    COMMAND_GET_VERSION = 0x01 # [] -> [03 09]
    # COMMAND_UNKNOWN1 = 0x02 # [] -> [00] ???
    COMMAND_TURN_ON = 0x03 # [] -> 00/01 (01 - ok)
    COMMAND_TURN_OFF = 0x04 # [] -> 00/01 (01 - ok)
    COMMAND_SET_MAIN_MODE = 0x05 # [04(mode) 00 23(target_temp) 00 00 00 00 00 00 00 00 00 00 80 00 00] -> 00/01 (01 - ok)
    COMMAND_GET_STATUS = 0x06 #   [] -> [04(mode) 00 23(target_temp) 00 01(sound_enabled) 5D(temp) 3C00(color_interval) 02(is_on) 00 00 00 00 80(boil_time) 00 00]
    COMMAND_GET_AUTO_OFF_HOURS = 0x30 # #  = 0x30          [] -> 0100, [] -> 1800, 0800
    COMMAND_SET_COLORS = 0x32
    COMMAND_GET_COLORS = 0x33
    COMMAND_SET_COLOR_INTERVAL = 0x34 #         # 1E 00 -> 00, 3C00 -> 00, 5A00, 7800
    COMMAND_GET_LIGHT_SWITCH = 0x35 #         C8 -> [c8 00 00/01 c8 00] - включена ли световая индикация
                            #       00 -> [00 00 00/01 00 00] - включена ли подсветка кипячения
                            #       01 -> [01 00 01 01 00] - запрос чего-то ещё???
    COMMAND_COMMIT_SETTINGS = 0x36 # [] -> 01   - после смены цвета, сохранение-обновление?
    COMMAND_SET_LIGHT_SWITCH = 0x37 # [00 00 00/01] - подсветка кипячения, [C8 C8 00/01] - световая индикация -> [00]

    COMMAND_IMPULSE_COLOR = 0x38 # [63(r) 00(g) DF(b) FF(brightness) 0000(fade interval)] -> 01
    COMMAND_SET_AUTO_OFF_HOURS = 0x39 # [18(hours) 00] -> 00
    COMMAND_SET_SOUND = 0x3C # [00/01] -> 01
    COMMAND_GET_STATS1 = 0x47
    COMMAND_GET_STATS2 = 0x50
    COMMAND_SET_FRESH_WATER = 0x51 # [00 00/01 30 00 00 00 00 00 00 00 00 00 00 00 00 00] -> [00 00]
    COMMAND_GET_FRESH_WATER = 0x52 # 00 -> [00 00/01 3000000000000000000000000000]
    COMMAND_SYNC_TIME = 0x6E # [7548D761(unix_timestamp) 302A0000(offset_minutes)] -> 00
    COMMAND_GET_TIME = 0x6F
    COMMAND_GET_SCHEDULE_RECORD = 0x70 # [xx] -> [24 57 D7 61 01 01 00 00 00 0F 01 00 00 00 00 00]
    COMMAND_ADD_SCHEDULE_RECORD = 0x71 # [14 58 D7 61 00 01 00 00 00 0F 01 00 00 00 00 00] -> [02 00]
    COMMAND_GET_SCHEDULE_COUNT = 0x73 # [] -> [07 0A 01 00 00 00 00 00 00 00 00 00 00 00 00 00]
    COMMAND_DEL_SCHEDULE_RECORD  = 0x74 # [00] -> [07] ???
    COMMAND_AUTH = 0xFF # [0000000000000000(password)]-> 00/01 (01 - ok)

    ColorsSet = namedtuple("ColorsSet", ["light_type",
        "temp_low", "brightness", "r_low", "g_low", "b_low",
        "temp_mid", "unknown1", "r_mid", "g_mid", "b_mid",
        "temp_high", "unknown2", "r_high", "g_high", "b_high"])
    Status = namedtuple("Status", ["mode", "target_temp", "sound_enabled", "current_temp",
        "color_interval", "is_on", "boil_time"])
    Stats = namedtuple("Stats", ["ontime", "energy_wh", "heater_on_count", "user_on_count"])
    FreshWaterInfo = namedtuple("FreshWaterInfo", ["is_on", "unknown1", "water_hours"])

    @abstractmethod
    async def command(self, command, params=[]):
        pass

    async def auth(self, key):
        r = await self.command(SkyKettle.COMMAND_AUTH, key)
        ok = r[0] == 1
        _LOGGER.debug(f"Auth: ok={ok}")
        return ok

    async def get_version(self):
        r = await self.command(SkyKettle.COMMAND_GET_VERSION)
        major, minor = unpack("BB", r)
        ver = f"{major}.{minor}"
        _LOGGER.debug(f"Version: {ver}")
        return (major, minor)

    async def turn_on(self):
        r = await self.command(SkyKettle.COMMAND_TURN_ON)
        if r[0] != 1: raise SkyKettleError("can't turn on")
        _LOGGER.debug(f"Turned on")

    async def turn_off(self):
        r = await self.command(SkyKettle.COMMAND_TURN_OFF)
        if r[0] != 1: raise SkyKettleError("can't turn off")
        _LOGGER.debug(f"Turned off")

    async def set_main_mode(self, mode, target_temp = 0, boil_time = 0):
        data = pack("BxBxxxxxxxxxxBxx", int(mode), int(target_temp), int(0x80 + boil_time))
        r = await self.command(SkyKettle.COMMAND_SET_MAIN_MODE, data)
        if r[0] != 1: raise SkyKettleError("can't set mode")
        _LOGGER.debug(f"Mode set: mode={mode} ({SkyKettle.MODE_NAMES[mode]}), target_temp={target_temp}, boil_time={boil_time}")

    async def get_status(self):
        r = await self.command(SkyKettle.COMMAND_GET_STATUS)
        status = SkyKettle.Status(*unpack("<BxBx?BHBxxxxBxx", r))
        status = status._replace(
            is_on = status.is_on == 2,
            boil_time = status.boil_time - 0x80
        )
        _LOGGER.debug(f"Status: mode={status.mode} ({SkyKettle.MODE_NAMES[status.mode]}), is_on={status.is_on}, "+
                     f"target_temp={status.target_temp}, current_temp={status.current_temp}, sound_enabled={status.sound_enabled}, "+
                     f"color_interval={status.color_interval}, boil_time={status.boil_time}")
        return status

    async def sync_time(self):
        t = time.localtime()
        offset = calendar.timegm(t) - calendar.timegm(time.gmtime(time.mktime(t)))
        now = int(time.time())
        data = pack("<ii", now, offset)
        r = await self.command(SkyKettle.COMMAND_SYNC_TIME, data)
        # r = await self.command(SkyKettle.COMMAND_SYNC_TIME,
        #    list(now.to_bytes(4, byteorder='little')) +
        #     list(offset.to_bytes(4, byteorder='little', signed=True)))
        if r[0] != 0: raise SkyKettleError("can't sync time")
        _LOGGER.debug(f"Writed time={now} ({datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')}), offset={offset} (GMT{offset/60/60:+.2f})")

    async def get_time(self):
        r = await self.command(SkyKettle.COMMAND_GET_TIME)
        t, offset = unpack("<ii", r)
        _LOGGER.debug(f"time={t} ({datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')}), offset={offset} (GMT{offset/60/60:+.2f})")
        return t, offset

    async def set_lamp_auto_off_hours(self, hours):
        data = pack("<H", hours)
        r = await self.command(SkyKettle.COMMAND_SET_AUTO_OFF_HOURS, data)
        if r[0] != 0: raise SkyKettleError("can't set lamp auto off hours")
        _LOGGER.debug(f"Updated lamp auto off hours={hours}")

    async def get_lamp_auto_off_hours(self):
        r = await self.command(SkyKettle.COMMAND_GET_AUTO_OFF_HOURS)
        hours, = unpack("<H", r)
        _LOGGER.debug(f"Lamp auto off hours={hours}")
        return hours

    async def get_colors(self, light_type):
        r = await self.command(SkyKettle.COMMAND_GET_COLORS, [light_type])
        colors_set = SkyKettle.ColorsSet(*unpack("BBBBBBBBBBBBBBBB", r))
        _LOGGER.debug(f"Colors set: {colors_set}")
        return colors_set

    async def set_colors(self, colors_set):
        data = pack("BBBBBBBBBBBBBBBB", *colors_set)
        r = await self.command(SkyKettle.COMMAND_SET_COLORS, data)
        if r[0] != 0: raise SkyKettleError("can't set colors")
        _LOGGER.debug(f"Updated colors set: {colors_set}")

    async def commit(self):
        r = await self.command(SkyKettle.COMMAND_COMMIT_SETTINGS)
        if r[0] != 1: raise SkyKettleError("can't commit settings")
        _LOGGER.debug(f"Settings commited")

    async def set_lamp_color_interval(self, secs):
        data = pack("<H", secs)
        r = await self.command(SkyKettle.COMMAND_SET_COLOR_INTERVAL, data)
        if r[0] != 0: raise SkyKettleError("can't set lamp color change interval")
        _LOGGER.debug(f"Updated lamp color interval secs={secs}")

    async def impulse_color(self, r, g, b, brightness=0xff, interval=0):
        data = pack("<BBBBH", r, g, b, brightness, interval)
        r = await self.command(SkyKettle.COMMAND_IMPULSE_COLOR, data)
        if r[0] != 1: raise SkyKettleError("can't fire color impulse")
        _LOGGER.debug(f"Impulse! r={r}, g={g}, b={b}, brightness={brightness}, interval={interval}")

    async def set_light_switch(self, light_type, on):
        data = pack("BB?", light_type, light_type, on)
        r = await self.command(SkyKettle.COMMAND_SET_LIGHT_SWITCH, data)
        if r[0] != 0: raise SkyKettleError("can't switch light")
        _LOGGER.debug(f"Light with type={light_type} ({SkyKettle.LIGHT_NAMES[light_type]}) switched {'on' if on else 'off'}")

    async def get_light_switch(self, light_type):
        data = pack("B", light_type)
        r = await self.command(SkyKettle.COMMAND_GET_LIGHT_SWITCH, data)
        is_on, = unpack("xx?xx", r)
        _LOGGER.debug(f"Light with type={light_type} ({SkyKettle.LIGHT_NAMES[light_type]}) is {'on' if is_on else 'off'}")
        return is_on

    async def set_sound(self, on):
        data = pack("?", on)
        r = await self.command(SkyKettle.COMMAND_SET_SOUND, data)
        if r[0] != 1: raise SkyKettleError("can't switch sound")
        _LOGGER.debug(f"Sound switched {'on' if on else 'off'}")

    async def set_fresh_water(self, on, unknown1=48):
        data = pack("<x?Hxxxxxxxxxxxx", on, int(unknown1))
        r = await self.command(SkyKettle.COMMAND_SET_FRESH_WATER, data)
        _LOGGER.debug(f"Fresh water notification switched {'on' if on else 'off'}")

    async def get_fresh_water(self):
        r = await self.command(SkyKettle.COMMAND_GET_FRESH_WATER, [0x00])
        info = SkyKettle.FreshWaterInfo(*unpack("<x?HHxxxxxxxxxx", r))
        _LOGGER.debug(f"Fresh water notification is {'on' if info.is_on else 'off'}, unknown1={info.unknown1}, water_hours={info.water_hours}")
        return info

    async def get_stats(self):
        r1 = await self.command(SkyKettle.COMMAND_GET_STATS1, [0x00])
        stats1 = unpack("<xxLLLxx", r1)
        r2 = await self.command(SkyKettle.COMMAND_GET_STATS2, [0x00])
        stats2 = unpack("<xxxLxxxxxxxxx", r2)
        stats = SkyKettle.Stats(*(stats1 + stats2))
        stats = stats._replace(ontime=timedelta(seconds=stats.ontime))
        _LOGGER.debug(f"Stats: ontime={stats.ontime}, energy_wh={stats.energy_wh}, user_on_count={stats.user_on_count}, heater_on_count={stats.heater_on_count}")
        return stats


class SkyKettleError(Exception):
    pass
