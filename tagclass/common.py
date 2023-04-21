from pathlib import Path
from typing import NewType

# typing
Engine = NewType('Engine', str)
Label = NewType('Label', str)

# default voc file
DATA_PATH = Path(__file__).parent / "data"
FAMILY_VOC_FILE = DATA_PATH / 'family_voc.toml'
LOCATOR_VOC_FILE = DATA_PATH / 'locator_voc.toml'
MISC_VOC_FILE = DATA_PATH / 'misc_voc.toml'
VOC_FILES = [LOCATOR_VOC_FILE, FAMILY_VOC_FILE, MISC_VOC_FILE]

# default init voc file
INIT_MISC_VOC_FILE = DATA_PATH / 'init_misc.toml'
INIT_LOCATOR_VOC_FILE = DATA_PATH / 'init_locator.toml'
INIT_VOC_FILES = [INIT_LOCATOR_VOC_FILE, INIT_MISC_VOC_FILE]