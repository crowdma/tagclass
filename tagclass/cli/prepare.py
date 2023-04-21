'''
pyarrow==11.0.0
'''
import json
import typer
import pyarrow as pa
import pyarrow.parquet as pq
from collections import defaultdict
from timeit import default_timer
from rich import progress, print

app = typer.Typer(add_completion=False)


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


@app.command()
def main(
    vtapiv2: str,
    prefix: str = 'maltree',
):
    label_engines = defaultdict(set)
    samples = 0
    # reading
    with Timer('Read'):
        with progress.open(
                vtapiv2,
                'r',
                description='Reading...',
        ) as f:
            for line in f:
                try:
                    scans = json.loads(line.strip())['scans']
                except json.JSONDecodeError:
                    continue
                samples += 1
                for engine, res in scans.items():
                    if not res['detected']:
                        continue
                    label = res['result']
                    # filter
                    if (label is None) or (len(label) < 3):
                        continue
                    # engines
                    label_engines[label].add(engine)
    # saving
    print(f'Total samples = {samples}')
    print(f'Total labels = {len(label_engines)}')
    labels = []
    engines = []
    for k, v in label_engines.items():
        labels.append(k)
        engines.append(sorted(v))
    table = pa.table({'label': labels, 'engines': engines})
    save_name = f"{prefix}-label-engines.parquet"
    with Timer('Save'):
        pq.write_table(
            table,
            save_name,
            compression=None,
        )
    # test read
    with Timer('Read'):
        data = pq.read_table(save_name)


if __name__ == '__main__':
    app()