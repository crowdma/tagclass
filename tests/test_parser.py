from typing import List

from pathlib import Path

from tagclass.parser import Parser, Result
from tagclass.tag import Vocabulary, TagScore
from tagclass.tokenizer import Tokenizer

TEST_VOC_FILE = Path(__file__).parent / "data" / "testvoc.toml"
voc = Vocabulary([TEST_VOC_FILE])
tokenize = Tokenizer()
tagparse = Parser(tokenize)
DATA_PATH = Path(__file__).parent / "data"


def assert_parse(result: List[Result], gt: List[Result]):
    for r, g in zip(result, gt):
        assert r == g


def test_parse():
    engine = 'default'
    labels = [
        'Backdoor:Win32/Darkshell',
        'Dropper:Win32/Anserver',
        'backdoor/androidos',
        'lotoor',
        'hacktool/lotoor',
        'lotoor',
        'ransom.wannacry.win32',
        'backdoor.generic.kungfu.android',
    ]
    gts = [
        [
            Result('backdoor', 'behavior', TagScore.CONFIRMED),
            Result('win', 'platform', TagScore.CONFIRMED),
            Result('darkshell', 'family', TagScore.LOCATORS_SEARCHED),
        ],
        [
            Result('dropper', 'behavior', TagScore.CONFIRMED),
            Result('win', 'platform', TagScore.CONFIRMED),
            Result('anserver', 'family', TagScore.LOCATORS_SEARCHED),
        ],
        [
            Result('backdoor', 'behavior', TagScore.CONFIRMED),
            Result('androidos', 'platform', TagScore.CONFIRMED),
        ],
        [
            Result('lotoor', 'family', TagScore.NO_LOCATOR_SEARCHED),
        ],
        [
            Result('hacktool', 'behavior', TagScore.CONFIRMED),
            Result('lotoor', 'family', TagScore.SINGLE_LOCATOR_SEARCHED),
        ],
        [
            Result('lotoor', 'family', TagScore.SINGLE_LOCATOR_SEARCHED),
        ],
        [
            Result('ransom', 'behavior', TagScore.CONFIRMED),
            Result('wannacry', 'family', TagScore.LOCATORS_SEARCHED),
            Result('win', 'platform', TagScore.CONFIRMED),
        ],
        [
            Result('backdoor', 'behavior', TagScore.CONFIRMED),
            Result('generic', 'misc', TagScore.CONFIRMED),
            Result('kungfu', 'family', TagScore.LOCATORS_SEARCHED),
            Result('android', 'platform', TagScore.CONFIRMED),
        ],
    ]
    for lb, gt in zip(labels, gts):
        result = tagparse.parse(lb, engine, voc)
        assert_parse(result, gt)

    assert str(voc.get('darkshell').abspath) == '/family/darkshell'