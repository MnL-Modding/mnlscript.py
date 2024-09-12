import re


PADDING_TEXT_TABLE_ID = 0x49


FEVENT_SCRIPT_NAME_REGEX = re.compile(r"([0-9a-fA-F]+)(?:_(\d+))?")
