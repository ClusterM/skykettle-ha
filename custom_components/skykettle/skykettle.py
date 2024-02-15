import calendar
import logging
import time
from abc import abstractmethod
from collections import namedtuple
from datetime import datetime, timedelta
from struct import pack, unpack

_LOGGER = logging.getLogger(__name__)


class SkyKettle():
    MODELS_1 = "models_1"
    MODELS_2 = "models_2"
    MODELS_3 = "models_3"
    MODELS_4 = "models_4"

    MODEL_TYPE = { # Source: https://github.com/KomX/ESPHome-Ready4Sky/blob/main/components/skykettle/__init__.py
        #"RK-M123S": MODELS_1, # need more investigation
        #"RK-M170S": MODELS_1, # need more investigation
        "RK-M171S": MODELS_2, # not 1
        #"RK-M173S": MODELS_2, # need more investigation
        "RK-G200":  MODELS_3,
        "RK-G200S": MODELS_4,
        "RK-G201S": MODELS_4,
        "RK-G202S": MODELS_4,
        "RK-G203S": MODELS_4,
        "RK-G204S": MODELS_4,
        "RK-G210S": MODELS_4,
        "RK-G211S": MODELS_4,
        "RK-G212S": MODELS_4,
        "RK-G213S": MODELS_4,
        "RK-G214S": MODELS_4,
        "RK-G215S": MODELS_4,
        "RFS-KKL002": MODELS_4,
        "RFS-KKL003": MODELS_4,
        "RFS-KKL004": MODELS_4,
        "RK-G233S": MODELS_4,
        "RK-G240S": MODELS_4,
        "RK-M215S": MODELS_4,
        "RK-M216S": MODELS_4,
        "RK-M223S": MODELS_4,
        "RK-M136S": MODELS_4,
        "RK-M139S": MODELS_4,
    }

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

    COMMAND_GET_VERSION = 0x01
    # COMMAND_UNKNOWN1 = 0x02 # [] -> [00] ???
    COMMAND_TURN_ON = 0x03
    COMMAND_TURN_OFF = 0x04
    COMMAND_SET_MAIN_MODE = 0x05
    COMMAND_GET_STATUS = 0x06
    COMMAND_GET_AUTO_OFF_HOURS = 0x30
    COMMAND_SET_COLORS = 0x32
    COMMAND_GET_COLORS = 0x33
    COMMAND_SET_COLOR_INTERVAL = 0x34
    COMMAND_GET_LIGHT_SWITCH = 0x35
    COMMAND_COMMIT_SETTINGS = 0x36
    COMMAND_SET_LIGHT_SWITCH = 0x37
    COMMAND_IMPULSE_COLOR = 0x38
    COMMAND_SET_AUTO_OFF_HOURS = 0x39
    COMMAND_SET_SOUND = 0x3C
    COMMAND_GET_STATS1 = 0x47
    COMMAND_GET_STATS2 = 0x50
    COMMAND_SET_FRESH_WATER = 0x51
    COMMAND_GET_FRESH_WATER = 0x52
    COMMAND_SYNC_TIME = 0x6E
    COMMAND_GET_TIME = 0x6F
    COMMAND_GET_SCHEDULE_RECORD = 0x70
    COMMAND_ADD_SCHEDULE_RECORD = 0x71
    COMMAND_GET_SCHEDULE_COUNT = 0x73
    COMMAND_DEL_SCHEDULE_RECORD  = 0x74
    COMMAND_AUTH = 0xFF

    ColorsSet = namedtuple("ColorsSet", ["light_type",
        "temp_low", "brightness", "r_low", "g_low", "b_low",
        "temp_mid", "unknown1", "r_mid", "g_mid", "b_mid",
        "temp_high", "unknown2", "r_high", "g_high", "b_high"])
    Status = namedtuple("Status", ["mode", "target_temp", "sound_enabled", "current_temp",
        "color_interval", "parental_control", "is_on", "error_code", "boil_time"])
    Stats = namedtuple("Stats", ["ontime", "energy_wh", "heater_on_count", "user_on_count"])
    FreshWaterInfo = namedtuple("FreshWaterInfo", ["is_on", "unknown1", "water_freshness_hours"])


    def __init__(self, model):
        _LOGGER.info(f"Kettle model: {model}")
        self.model = model
        self.model_code = self.get_model_code(model)
        if not self.model_code:
            raise SkyKettleError("Unknown kettle model")

    @staticmethod
    def get_model_code(model):
        if model in SkyKettle.MODEL_TYPE:
            return SkyKettle.MODEL_TYPE[model]
        if model.endswith("-E"):
            return SkyKettle.MODEL_TYPE.get(model[:-2], None)
        return None

    @abstractmethod
    async def command(self, command, params=[]):
        pass

    async def auth(self, key):
        r = await self.command(SkyKettle.COMMAND_AUTH, key)
        ok = r[0] != 0
        _LOGGER.debug(f"Auth: ok={ok}")
        return ok

    async def get_version(self):
        r = await self.command(SkyKettle.COMMAND_GET_VERSION)
        major, minor = unpack("BB", r)
        ver = f"{major}.{minor}"
        _LOGGER.debug(f"Version: {ver}")
        return (major, minor)

    async def turn_on(self):
        if self.model_code in [SkyKettle.MODELS_3, SkyKettle.MODELS_4]: # All except RK-M171S, RK-M172S, RK-M173S
            r = await self.command(SkyKettle.COMMAND_TURN_ON)
            if r[0] != 1: raise SkyKettleError("can't turn on")
            _LOGGER.debug(f"Turned on")
        else:
            _LOGGER.debug(f"turn_on is not supported by this model")

    async def turn_off(self):
        if self.model_code in [SkyKettle.MODELS_1, SkyKettle.MODELS_2, SkyKettle.MODELS_3, SkyKettle.MODELS_4]: # All known models
            r = await self.command(SkyKettle.COMMAND_TURN_OFF)
            if r[0] != 1: raise SkyKettleError("can't turn off")
            _LOGGER.debug(f"Turned off")
        else:
            _LOGGER.debug(f"turn_off is not supported by this model")

    async def set_main_mode(self, mode, target_temp = 0, boil_time = 0):
        if self.model_code in [SkyKettle.MODELS_1, SkyKettle.MODELS_2]: # RK-M170S, RK-M171S and RK-M173S but not sure about RK-M170S and RK-M173S
            if mode == SkyKettle.MODE_BOIL_HEAT:
                mode = SkyKettle.MODE_BOIL # MODE_BOIL_HEAT not supported
            elif mode == SkyKettle.MODE_BOIL:
                target_temp = 0
        if self.model_code in [SkyKettle.MODELS_1]: # RK-M170S (?)
            if target_temp == 0:
                pass
            elif target_temp < 50:
                target_temp = 1
            elif target_temp < 65:
                target_temp = 2
            elif target_temp < 80:
                target_temp = 3
            elif target_temp < 90:
                target_temp = 4
            else:
                target_temp = 5
        if self.model_code in [SkyKettle.MODELS_1]: # RK-M170S and 
            data = pack("BBxx", int(mode), int(target_temp))
        if self.model_code in [SkyKettle.MODELS_2, SkyKettle.MODELS_3]: # RK-M171S, RK-M173S and RK-G200
            data = pack("BxBx", int(mode), int(target_temp))
        elif self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S
            data = pack("BxBxxxxxxxxxxBxx", int(mode), int(target_temp), int(0x80 + boil_time))
        else:
            _LOGGER.debug(f"set_main_mode is not supported by this model")
            return
        r = await self.command(SkyKettle.COMMAND_SET_MAIN_MODE, data)
        if r[0] != 1: raise SkyKettleError("can't set mode")
        _LOGGER.debug(f"Mode set: mode={mode} ({SkyKettle.MODE_NAMES[mode]}), target_temp={target_temp}, boil_time={boil_time}")

    async def get_status(self):
        r = await self.command(SkyKettle.COMMAND_GET_STATUS)
        # if self.model_code in [MODELS_1] # ???
        if self.model_code in [SkyKettle.MODELS_2, SkyKettle.MODELS_3]: # RK-M173S (?), RK-G200
            mode, target_temp, is_on, current_temp = unpack("<BxBxxxxx?xBxxxxx", r)
            status = SkyKettle.Status(mode=mode,
                target_temp=target_temp,
                current_temp=current_temp,
                sound_enabled=None,
                color_interval=None,
                parental_control=False,
                is_on=is_on,
                error_code=None,
                boil_time=None)
        elif self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S
            # New models
            status = SkyKettle.Status(*unpack("<BxBx?BB??BxxxBxx", r))
            status = status._replace(
                boil_time = status.boil_time - 0x80,
                error_code=None if status.error_code == 0 else status.error_code
            )
        else:
            _LOGGER.debug(f"get_status is not supported by this model")
            return
        if self.model_code in [SkyKettle.MODELS_2, SkyKettle.MODELS_3]: # RK-M173S (?), RK-G200
            if status.mode == SkyKettle.MODE_BOIL and status.target_temp > 0:
                status = status._replace(
                    mode=SkyKettle.MODE_BOIL_HEAT
                )
        if self.model_code in [SkyKettle.MODELS_1]: # RK-M170S (?)
            if status.target_temp == 1:
                target_temp = 40
            elif status.target_temp == 2:
                target_temp = 55
            elif status.target_temp == 3:
                target_temp = 70
            elif status.target_temp == 4:
                target_temp = 85
            elif status.target_temp == 5:
                target_temp = 90
            else:
                target_temp = 0
            status = status._replace(
                target_temp=target_temp
            )
        _LOGGER.debug(f"Status: mode={status.mode} ({SkyKettle.MODE_NAMES[status.mode]}), is_on={status.is_on}, "+
                     f"target_temp={status.target_temp}, current_temp={status.current_temp}, sound_enabled={status.sound_enabled}, "+
                     f"color_interval={status.color_interval}, boil_time={status.boil_time}")
        return status

    async def sync_time(self):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S
            t = time.localtime()
            offset = calendar.timegm(t) - calendar.timegm(time.gmtime(time.mktime(t)))
            now = int(time.time())
            data = pack("<ii", now, offset)
            r = await self.command(SkyKettle.COMMAND_SYNC_TIME, data)
            if r[0] != 0: raise SkyKettleError("can't sync time")
            _LOGGER.debug(f"Writed time={now} ({datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')}), offset={offset} (GMT{offset/60/60:+.2f})")
        else:
            _LOGGER.debug(f"sync_time is not supported by this model")

    async def get_time(self):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            r = await self.command(SkyKettle.COMMAND_GET_TIME)
            t, offset = unpack("<ii", r)
            _LOGGER.debug(f"time={t} ({datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')}), offset={offset} (GMT{offset/60/60:+.2f})")
            return t, offset
        else:
            _LOGGER.debug(f"get_time is not supported by this model")

    async def set_lamp_auto_off_hours(self, hours):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            data = pack("<H", int(hours))
            r = await self.command(SkyKettle.COMMAND_SET_AUTO_OFF_HOURS, data)
            if r[0] != 0: raise SkyKettleError("can't set lamp auto off hours")
            _LOGGER.debug(f"Updated lamp auto off hours={hours}")
        else:
            _LOGGER.debug(f"set_lamp_auto_off_hours is not supported by this model")

    async def get_lamp_auto_off_hours(self):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            r = await self.command(SkyKettle.COMMAND_GET_AUTO_OFF_HOURS)
            hours, = unpack("<H", r)
            _LOGGER.debug(f"Lamp auto off hours={hours}")
            return hours
        else:
            _LOGGER.debug(f"get_lamp_auto_off_hours is not supported by this model")

    async def get_colors(self, light_type):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            r = await self.command(SkyKettle.COMMAND_GET_COLORS, [light_type])
            colors_set = SkyKettle.ColorsSet(*unpack("BBBBBBBBBBBBBBBB", r))
            _LOGGER.debug(f"{colors_set}")
            return colors_set
        else:
            _LOGGER.debug(f"get_colors is not supported by this model")

    async def set_colors(self, colors_set):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            data = pack("BBBBBBBBBBBBBBBB", *colors_set)
            r = await self.command(SkyKettle.COMMAND_SET_COLORS, data)
            if r[0] != 0: raise SkyKettleError("can't set colors")
            _LOGGER.debug(f"Updated colors set: {colors_set}")
        else:
            _LOGGER.debug(f"set_colors is not supported by this model")

    async def commit(self):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            r = await self.command(SkyKettle.COMMAND_COMMIT_SETTINGS)
            if r[0] != 1: raise SkyKettleError("can't commit settings")
            _LOGGER.debug(f"Settings commited")
        else:
            _LOGGER.debug(f"commit is not supported by this model")

    async def set_lamp_color_interval(self, secs):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            data = pack("<H", int(secs))
            r = await self.command(SkyKettle.COMMAND_SET_COLOR_INTERVAL, data)
            if r[0] != 0: raise SkyKettleError("can't set lamp color change interval")
            _LOGGER.debug(f"Updated lamp color interval secs={secs}")
        else:
            _LOGGER.debug(f"set_lamp_color_interval is not supported by this model")

    async def impulse_color(self, r, g, b, brightness=0xff, interval=0):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            data = pack("<BBBBH", r, g, b, brightness, interval)
            r = await self.command(SkyKettle.COMMAND_IMPULSE_COLOR, data)
            if r[0] != 1: raise SkyKettleError("can't fire color impulse")
            _LOGGER.debug(f"Impulse! r={r}, g={g}, b={b}, brightness={brightness}, interval={interval}")
        else:
            _LOGGER.debug(f"impulse_color is not supported by this model")

    async def set_light_switch(self, light_type, on):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            data = pack("BB?", light_type, light_type, on)
            r = await self.command(SkyKettle.COMMAND_SET_LIGHT_SWITCH, data)
            if r[0] != 0: raise SkyKettleError("can't switch light")
            _LOGGER.debug(f"Light with type={light_type} ({SkyKettle.LIGHT_NAMES[light_type]}) switched {'on' if on else 'off'}")
        else:
            _LOGGER.debug(f"set_light_switch is not supported by this model")

    async def get_light_switch(self, light_type):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            data = pack("B", light_type)
            r = await self.command(SkyKettle.COMMAND_GET_LIGHT_SWITCH, data)
            is_on, = unpack("xx?xx", r)
            _LOGGER.debug(f"Light with type={light_type} ({SkyKettle.LIGHT_NAMES[light_type]}) is {'on' if is_on else 'off'}")
            return is_on
        else:
            _LOGGER.debug(f"get_light_switch is not supported by this model")

    async def set_sound(self, on):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            data = pack("?", on)
            r = await self.command(SkyKettle.COMMAND_SET_SOUND, data)
            if r[0] != 1: raise SkyKettleError("can't switch sound")
            _LOGGER.debug(f"Sound switched {'on' if on else 'off'}")
        else:
            _LOGGER.debug(f"set_sound is not supported by this model")

    async def set_fresh_water(self, on, unknown1=48):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            data = pack("<x?Hxxxxxxxxxxxx", on, int(unknown1))
            r = await self.command(SkyKettle.COMMAND_SET_FRESH_WATER, data)
            _LOGGER.debug(f"Fresh water notification switched {'on' if on else 'off'}")
        else:
            _LOGGER.debug(f"set_fresh_water is not supported by this model")

    async def get_fresh_water(self):
        if self.model_code in [SkyKettle.MODELS_4]: # RK-G2xxS, RK-M13xS, RK-M21xS, RK-M223S but not sure
            r = await self.command(SkyKettle.COMMAND_GET_FRESH_WATER, [0x00])
            info = SkyKettle.FreshWaterInfo(*unpack("<x?HHxxxxxxxxxx", r))
            _LOGGER.debug(f"Fresh water notification is {'on' if info.is_on else 'off'}, unknown1={info.unknown1}, water_freshness_hours={info.water_freshness_hours}")
            return info
        else:
            _LOGGER.debug(f"get_fresh_water is not supported by this model")

    async def get_stats(self):
        if self.model_code in [SkyKettle.MODELS_4]: # Not sure
            r1 = await self.command(SkyKettle.COMMAND_GET_STATS1, [0x00])
            stats1 = unpack("<xxLLLxx", r1)
            r2 = await self.command(SkyKettle.COMMAND_GET_STATS2, [0x00])
            stats2 = unpack("<xxxLxxxxxxxxx", r2)
            stats = SkyKettle.Stats(*(stats1 + stats2))
            stats = stats._replace(ontime=timedelta(seconds=stats.ontime))
            _LOGGER.debug(f"Stats: ontime={stats.ontime}, energy_wh={stats.energy_wh}, user_on_count={stats.user_on_count}, heater_on_count={stats.heater_on_count}")
            return stats
        else:
            _LOGGER.debug(f"get_stats is not supported by this model")


class SkyKettleError(Exception):
    pass
