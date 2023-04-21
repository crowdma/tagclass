from pathlib import Path
from tagclass.tag import Vocabulary, TagScore, TagEntity

TEST_VOC_FILE = Path(__file__).parent / "data" / "testvoc.toml"


def test_vocabulary():
    voc = Vocabulary([TEST_VOC_FILE])
    assert len(voc) == 69
    assert voc['ransom'].entity == TagEntity.BEHAVIOR
    voc.add('agent', entity=TagEntity.MISC, path='generic')
    assert str(voc.get_or_create(
        'agent').abspath) == f'/{TagEntity.MISC}/generic/agent'
    assert voc['ransom'].score == TagScore.CONFIRMED
    # dump
    voc.dump(TagEntity.keys(), TEST_VOC_FILE)
