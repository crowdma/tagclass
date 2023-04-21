from typing import List, Dict

import re
import json
import string
from rich import progress
from timeit import default_timer
from collections import defaultdict
from tagclass.common import Label, Engine


class Timer:
    __slots__ = ['msg', 'ndigits', 'start', 'end', 'elapsed']

    def __init__(self, msg: str = 'timecost', *, ndigits: int = 4):
        self.msg = msg
        self.ndigits = ndigits

    def __enter__(self):
        self.start = default_timer()
        return self

    def __exit__(self, exc_type, exc_value, trace):
        self.end = default_timer()
        self.elapsed = round(self.end - self.start, self.ndigits)
        print(f'{self.msg}: {self.elapsed} seconds')


def load_label_engines(vtapiv2_file: str) -> Dict[Label, List[Engine]]:
    label_engines = defaultdict(set)
    with progress.open(
            vtapiv2_file,
            'r',
            description='Reading...',
    ) as f:
        for line in f:
            try:
                vtapiv2 = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            try:
                scans: Dict = vtapiv2['scans']
            except KeyError:
                continue
            for engine, res in scans.items():
                if not res['detected']:
                    continue
                label = res['result']
                if not isinstance(label, str):
                    continue
                # clean
                label = ''.join(filter(lambda x: x in string.printable, label))
                # filter
                if len(label) < 3:
                    continue
                # engines
                label_engines[label].add(engine)
    # sorted
    return {k: sorted(v) for k, v in label_engines.items()}


def normalize_label_name(
    label: str,
    *,
    delimiter: str = '.',
    lower_case: bool = True,
    rstrip_decimal: bool = True,
    min_length: int = 3,
) -> str:
    sep = "[^a-zA-Z0-9]"
    decimal = '0123456789'
    token_list = []
    for token in re.split(sep, label):
        if rstrip_decimal:
            token = token.rstrip(decimal)
        if len(token) < min_length:
            continue
        if lower_case:
            token = token.lower()
        if token not in token_list:
            token_list.append(token)
    return delimiter.join(token_list)