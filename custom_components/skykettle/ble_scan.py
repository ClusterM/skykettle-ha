import subprocess
import asyncio
import re
from threading import Thread
from collections import namedtuple

REGEX_MAC = r"^(([0-9a-fA-F]){2}[:-]?){5}[0-9a-fA-F]{2}$"

BleDevice = namedtuple("BleDevice", ["mac", "name"])


class ScanThread(Thread):
    def __init__(self, scan_time, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scan_time = int(scan_time)
        self.result = None

    def run(self):
        proc = subprocess.Popen(["timeout", "-s", "INT", f"{self.scan_time}s", "hcitool", "lescan"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        self.result = proc.communicate()


async def ble_scan(scan_time=3):
    scan_thread = ScanThread(scan_time=scan_time, daemon=True)
    scan_thread.start()
    while not scan_thread.result: await asyncio.sleep(0.1)
    stdout, stderr = scan_thread.result
    out_lines = stdout.decode('utf-8').split('\n')
    err = stderr.decode('utf-8')
    if err:
        if "Operation not permitted" in err:
            raise PermissionError(err)
        else:
            raise Exception(err)
    res = []
    for l in out_lines:
        cols = l.split(maxsplit=2)
        if len(cols) >= 2 and re.match(REGEX_MAC, cols[0]):
            mac = cols[0]
            name = cols[1].replace('_',' ')
            if name == "(unknown)": name = None
            if len([l for l in res if l.mac == mac]) == 0:
                res.append(BleDevice(mac, name))

    return res
