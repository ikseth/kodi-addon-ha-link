import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(RAIZ, "addon", "service.ha_link")
sys.path.insert(0, os.path.join(ADDON, "resources", "lib"))
