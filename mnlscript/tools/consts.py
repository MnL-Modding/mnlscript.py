import pathlib
import re

from ..consts import FEVENT_SCRIPT_NAME_REGEX


DEFAULT_SCRIPTS_DIR_PATH = pathlib.Path("scripts")
FEVENT_SCRIPTS_DIR = "fevent"
BATTLE_SCRIPTS_DIR = "battle"
MENU_SCRIPTS_DIR = "menu"
SHOP_SCRIPTS_DIR = "shop"

FEVENT_SCRIPT_FILENAME_REGEX = re.compile(FEVENT_SCRIPT_NAME_REGEX.pattern + r"\.py")
