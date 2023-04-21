from typing import List

import re
import string
from tagclass.common import Engine, Label

LAST_DOT_REMOVE_ENGINES = {
    # ===
    'avast',
    'avira',
    'comodo',
    'eset-nod32',
    'fortinet',
    'gdata',
    'jiangmin',
    'kaspersky',
    'microsoft',
    'nano-antivirus',
    'norman',
    'sophos',
    'trendmicro',
    'trendmicro-housecall',
    # ===
    'avg',
    'alibaba',
}

LAST_REMOVE_DELIMTERS = ['@', '#', '!']


def clean_label(label: str) -> str:
    return ''.join(filter(lambda x: x in string.printable, label)).strip()


def remove_suffixes(engine: Engine, label: Label) -> Label:
    '''Remove label suffix
    '''
    # remove engine-specific last  '.'
    if engine in LAST_DOT_REMOVE_ENGINES:
        label = label.rsplit('.', 1)[0]
    # remove specific separator
    for sep in LAST_REMOVE_DELIMTERS:
        label = label.rsplit(sep, 1)[0]

    return label


def normalize_engine_name(name: str) -> str:
    sep = "[^a-zA-Z0-9]"
    token_list = re.split(sep, name)
    return ''.join(token_list).lower()


def hasdigit(name: str) -> bool:
    return any(c.isdigit() for c in name)


class Tokenizer:

    def __init__(self, max_seq_length: int = 16) -> None:
        self.max_seq_length = max_seq_length

    def separator(self, engine: Engine) -> str:
        # todo: engine-specific separator
        return "[^a-zA-Z0-9]"

    def run(self, engine: Engine, label: Label) -> List[str]:
        engine = normalize_engine_name(engine)
        label = clean_label(label)
        # suffix remove
        label = remove_suffixes(engine, label)
        # tokenize
        sep = self.separator(engine)
        tag_list = []
        count = 0
        for tag in re.split(sep, label):
            if count >= self.max_seq_length:
                break
            # 1.ignore not str
            if not isinstance(tag, str):
                continue
            # 2. ignore pure digits
            if tag.isdigit():
                continue
            # 3. ignore digits + ascii_uppercase
            # if hasdigit(tag) and tag.isupper():
            #     continue
            # 4. remove suffix digits
            tag = tag.rstrip('0123456789')
            # 5. check length
            if len(tag) < 3:
                continue
            # append lower
            tag = tag.lower()
            if tag not in tag_list:
                tag_list.append(tag)
                count += 1

        return tag_list
