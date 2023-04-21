from typing import Dict, Tuple

import typer
import json
from pathlib import Path
from rich import progress, print
from rich.table import Table
from dataclasses import asdict
from seqeval.metrics import accuracy_score, classification_report

from tagclass.tag import Vocabulary
from tagclass.parser import Parser
from tagclass.tokenizer import Tokenizer
from tagclass.common import VOC_FILES
from tagclass.utils import load_label_engines

app = typer.Typer()

ENTITY_MAP = {
    'behavior': 'B-BEH',
    'platform': 'B-PLA',
    'family': 'B-FAM',
    'misc': 'B-MISC',
    'outside': 'O',
}


def print_error_table(
    error: Dict[str, Tuple[str, str, str]],
    save_error: bool = False,
    *,
    title='error',
):
    error_table = Table(title=title)
    column_style = {
        'engine': 'cyan',
        'label': 'cyan',
        'tag': 'cyan',
        'truth': 'green',
        'predict': 'red',
    }
    for c, s in column_style.items():
        error_table.add_column(c, style=s)

    for t, data in error.items():
        value = data[:2] + [t] + data[2:]
        error_table.add_row(*value)
    print(error_table)
    if save_error:
        with open(Path.cwd() / 'error.log', 'w') as file:
            print(error_table, file=file)


@app.callback(invoke_without_command=True)
def main(
    label: str = None,
    engine: str = None,
    vtapiv2_file: str = None,
    truth_file: str = None,
    save_parse: bool = False,
    save_error: bool = False,
):
    if label is None and vtapiv2_file is None:
        print('Need a label or a vtapiv2_file file')
        raise typer.Exit(-1)

    parser = Parser(Tokenizer())
    voc = Vocabulary(VOC_FILES)
    if label:
        if engine is None:
            engine = 'default'
        result = parser.parse(label, engine, voc)
        print(result)

    if vtapiv2_file:
        label_engines = load_label_engines(vtapiv2_file)
        results = {}
        for label, engines in progress.track(
                label_engines.items(),
                total=len(label_engines),
                description='Parsing ...',
        ):
            parsed = parser.parse(label, engines[0], voc)
            results[label] = [asdict(p) for p in parsed]
        if save_parse:
            save_path = Path.cwd() / f'tagclass-parse.jsonl'
            with open(save_path, 'w') as f:
                for label, ner in progress.track(
                        results.items(),
                        total=len(results),
                        description='Saving...',
                ):
                    f.write(json.dumps([label, ner]) + '\n')
            print(f'Save result in {save_path}')
        if truth_file:
            ground = {}
            with open(truth_file, 'r') as f:
                for line in f:
                    label, ner = json.loads(line)
                    ground.update({label: ner})

            y_true = []
            y_pred = []
            error = {}
            for label, ner in ground.items():
                l_true = []
                l_pred = []
                for tag, entity in ner.items():
                    l_true.append(ENTITY_MAP[entity])
                    parsed = {i['tag']: i['entity'] for i in results[label]}
                    hat_entity = parsed[tag] if tag in parsed else 'outside'
                    l_pred.append(ENTITY_MAP[hat_entity])
                    if entity != hat_entity:
                        error[tag] = [
                            label_engines[label][0], label, entity, hat_entity
                        ]
                y_true.append(l_true)
                y_pred.append(l_pred)
            accuracy = accuracy_score(y_true, y_pred)
            report = classification_report(y_true, y_pred)
            print_error_table(error, save_error)
            print(f'number of error tags = {len(error)}')
            print(f'accuracy = {accuracy}')
            print(report)