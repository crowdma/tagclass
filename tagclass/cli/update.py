import typer

import json
import pyarrow.parquet as pq
from rich import print, progress

from tagclass.tag import TagScore, Vocabulary, LOCATORS
from tagclass.update import locator_incremental_update
from tagclass.common import VOC_FILES, LOCATOR_VOC_FILE
from tagclass.parser import RunMode
from tagclass.utils import load_label_engines

app = typer.Typer(add_completion=False)


@app.callback(invoke_without_command=True)
def main(
    vtapiv2_jsonl: str = None,
    label_engines_parquet: str = None,
    certs_json: str = None,
    cert_qos: int = 2,
    threshold_cfs: int = 6,
    max_round: int = 3,
    lfs_mode: str = RunMode.UPDATE,
    dump: bool = False,
    do_test: bool = False,
    verbose: int = 1,
):
    if certs_json:
        with open(certs_json, 'r') as f:
            certs = {
                k: sorted(v.items(), key=lambda x: x[1])[0][1]
                for k, v in json.load(f).items()
            }
            certs = {k for k, v in certs.items() if v >= cert_qos}
    else:
        certs = None
    if certs is not None:
        print(f'[*] certs = {len(certs)}')

    if vtapiv2_jsonl:
        label_engines = load_label_engines(vtapiv2_jsonl)
    elif label_engines_parquet:
        data = pq.read_table(label_engines_parquet)
        label_engines = {}
        count = 0
        for label, engines in progress.track(
                zip(data['label'], data['engines']),
                total=data.num_rows,
                description='Loading...',
        ):
            label_engines[label.as_py()] = engines.as_py()
            count += 1
            if do_test and count == 5000:
                break
    else:
        print('[x] Need label_engines!')
        raise typer.Exit(-1)

    print(f'[*] labels = {len(label_engines)}')
    # init vocabulary
    init_voc = Vocabulary(VOC_FILES)
    # loop
    round = 0
    round_updated_num = 1
    last_updated_set = set()
    while round_updated_num > 0:
        round += 1
        if round > max_round:
            break
        round_updated_num = 0
        print(f'\n========== Locator update round {round} ==========')
        # init
        print('// initial vocabulary')
        print(f"[*] {init_voc}")
        # incremental
        print("// LFS-CFS loop until no new locator")
        init_voc = locator_incremental_update(
            label_engines,
            voc=init_voc,
            threshold_cfs=threshold_cfs,
            lfs_mode=lfs_mode,
            verbose=verbose,
            certs=certs,
        )
        cumulative_updated_set = set([
            k for k, v in init_voc.value.items()
            if v.entity in LOCATORS and v.score == TagScore.UPDATED
        ])
        round_updated_set = cumulative_updated_set - last_updated_set
        round_updated_num = len(round_updated_set)
        last_updated_set = cumulative_updated_set
        # add
        print('// updated')
        print(f'[*] upated = {round_updated_num}')
        if verbose >= 1 and round_updated_num:
            print(round_updated_set)
    # dump
    if dump:
        init_voc.dump(LOCATORS, LOCATOR_VOC_FILE)
    # report
    print(f'// report')
    if round <= max_round:
        print(f'[-] LIU finishes at round {round}')

    else:
        print(f'[-] LIU exceeds max round {max_round}')
    print(f'[-] threshold_cfs = {threshold_cfs} | lfs_mode = {lfs_mode}')
