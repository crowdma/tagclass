from pathlib import Path
from tagclass.tag import Vocabulary, TagEntity, TagScore
from tagclass.update import locator_incremental_update

TEST_VOC_FILE = Path(__file__).parent / "data" / "testvoc.toml"


def test_locator_incremental_update():
    label_engines = {
        'win32.ransom.gandcrab': ['default'],
        'win.ransomtest.gandcrab': ['default'],
        'ransomtest.gandcrab': ['default'],
    }
    voc = Vocabulary([TEST_VOC_FILE])
    voc = locator_incremental_update(label_engines, voc, threshold_cfs=2)
    assert voc.get('ransomtest').entity == TagEntity.BEHAVIOR
    assert voc.get('ransomtest').score == TagScore.UPDATED