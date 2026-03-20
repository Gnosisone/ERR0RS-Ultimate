# ERR0RS WiFi Pineapple Nano Integration
# Full PineAP engine control, recon, capture, and module management
# For authorized red team WiFi engagements only

from .pineapple_client import PineappleClient
from .pineap_engine import PineAPEngine
from .recon import PineappleRecon
from .modules_manager import ModulesManager
from .pineapple_studio import PineappleStudio

__all__ = [
    "PineappleClient",
    "PineAPEngine",
    "PineappleRecon",
    "ModulesManager",
    "PineappleStudio",
]

__version__ = "1.0.0"
__author__ = "ERR0RS ULTIMATE"
__description__ = (
    "WiFi Pineapple Nano integration - PineAP engine, recon, "
    "client harvesting, and module management for red team WiFi ops"
)

# Default Pineapple Nano network config
PINEAPPLE_DEFAULT_IP   = "172.16.42.1"
PINEAPPLE_DEFAULT_PORT = 1471
PINEAPPLE_DEFAULT_USER = "root"
