"""Constants for SkyKettle component."""

DOMAIN = "skykettle"
FRIENDLY_NAME = "SkyKettle"
MANUFACTORER = "Redmond"
SUGGESTED_AREA = "kitchen"

REGEX_MAC = r"^(([0-9a-fA-F]){2}[:-]?){5}[0-9a-fA-F]{2}$"

CONF_PERSISTENT_CONNECTION = "persistent_connection"

DEFAULT_SCAN_INTERVAL = 5
DEFAULT_PERSISTENT_CONNECTION = True

DATA_CONNECTION = "connection"
DATA_CANCEL = "cancel"
DATA_WORKING = "working"
DATA_DEVICE_INFO = "device_info"

DISPATCHER_UPDATE = "update"

ROOM_TEMP = 25
BOIL_TEMP = 100

BLE_SCAN_TIME = 3