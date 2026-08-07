"""Constants for the RTI AD-4x integration."""
from __future__ import annotations

DOMAIN = "rti_ad4x"
DEFAULT_PORT = 23

CONF_MAC = "mac"
CONF_MODEL = "model"
CONF_FW_VERSION = "fw_version"
CONF_ZONES = "zones"
CONF_NAME = "name"

# Fixed by the product itself (confirmed via the device's own web UI:
# `rtiMaxPorts=4`) — not user-configurable.
NUM_ZONES = 4

VOL_MIN = 0
VOL_MAX = 75
TONE_MIN = -12
TONE_MAX = 12
TONE_STEP = 2

# RTI markets the AD-4x as "4 local + 4 remote" source inputs; the amp's
# *ZNzzSRCnn command range (1-8) matches this regardless of zone count.
NUM_SOURCES = 8
SOURCE_NAMES: dict[int, str] = {
    1: "Lokalne 1",
    2: "Lokalne 2",
    3: "Lokalne 3",
    4: "Lokalne 4",
    5: "Zdalne 1",
    6: "Zdalne 2",
    7: "Zdalne 3",
    8: "Zdalne 4",
}

DEFAULT_POLL_INTERVAL = 15  # seconds — no push notifications, must poll
