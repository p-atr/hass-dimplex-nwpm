"""Constants for the Dimplex NWPM Touch integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "dimplex_nwpm"
CONF_USE_MODBUS: Final = "use_modbus"

# Settings are not pushed by the gateway, so they are polled in addition.
POLL_INTERVAL: Final = timedelta(seconds=60)
