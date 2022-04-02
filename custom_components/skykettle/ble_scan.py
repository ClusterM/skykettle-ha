import subprocess
import asyncio
import shlex
import re
from collections import namedtuple

REGEX_MAC = r"^(([0-9a-fA-F]){2}[:-]?){5}[0-9a-fA-F]{2}$"

BleDevice = namedtuple("BleDevice", ["mac", "name"])
BleAdapter = namedtuple("BleAdapter", ["name", "mac"])


async def ble_scan(device, scan_time=3):
    devopt = ""
    if device: devopt = f"-i {shlex.quote(device)}"
    proc = await asyncio.create_subprocess_shell(
        f"timeout -s INT {int(scan_time)}s hcitool {devopt} lescan",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    out_lines = stdout.decode('utf-8').split('\n')
    err = stderr.decode('utf-8')

    res = []
    for l in out_lines:
        cols = l.split(maxsplit=2)
        if len(cols) >= 2 and re.match(REGEX_MAC, cols[0]):
            mac = cols[0]
            name = cols[1].replace('_',' ')
            if name == "(unknown)": name = None
            if len([l for l in res if l.mac == mac]) == 0:
                res.append(BleDevice(mac, name))

    if err and not res:
        if "Operation not permitted" in err:
            raise PermissionError(err)
        else:
            raise Exception(err)

    return res

async def ble_get_adapters():
    proc = await asyncio.create_subprocess_shell(
        "hcitool dev",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    out_lines = stdout.decode('utf-8').split('\n')
    err = stderr.decode('utf-8')
    if err: raise Exception(err)

    devices = []
    for line in out_lines:
        cols = line.split()
        if len(cols) >= 2 and re.match(REGEX_MAC, cols[1]):
            devices.append(BleAdapter(cols[0], cols[1]))
    return devices
