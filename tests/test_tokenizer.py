from tagclass.tokenizer import Tokenizer


def test_tokenizer():
    data = [
        (
            'Microsoft',
            'Worm:Win32/Silly.Gaa',
            ['worm', 'win', 'silly'],
        ),
        (
            'default',
            'Worm:Win32/Silly_12a23b',
            ['worm', 'win', 'silly', '12a23b'],
        ),
        (
            'Rising',
            'Trojan.Emotet!8.B95 (TFE:3:8TNkkv9OZTL)',
            ['trojan', 'emotet'],
        ),
        (
            'default',
            'Trojan.Emotet.trojan',
            ['trojan', 'emotet'],
        ),
    ]

    tokenizer = Tokenizer()
    for engine, label, expect in data:
        assert tokenizer.run(engine, label) == expect