import pyrootutils

root = pyrootutils.setup_root(
    search_from=__file__,
    indicator=[".git", "pyproject.toml"],
    pythonpath=True,
    dotenv=True,
)

from typing import List, Dict, Set, Tuple

import typer
import json
from rich import print
from rich.table import Table
from collections import defaultdict, namedtuple
from pathlib import Path
from tagclass.tokenizer import Tokenizer
from tagclass.update import locator_incremental_update
from tagclass.parser import Parser, LOCATORS, RunMode
from tagclass.tag import Vocabulary, TagScore, TagEntity
from tagclass.utils import load_label_engines
from tagclass.common import (
    INIT_MISC_VOC_FILE,
    INIT_LOCATOR_VOC_FILE,
)

app = typer.Typer()

# namedtuple
ParseResult = namedtuple("ParseResult", ['label', 'engine', 'family', 'score'])


def precision_recall(
    updated: Set[str],
    truth: Set[str],
    exist: Set[str],
    possible: Set[str],
):
    # precision focus on updated
    tp = truth & updated
    if len(updated) == 0:
        return {}
    metrics = {}
    metrics['precision'] = len(tp) / len(updated)
    # recall focus on all possible
    tpos = exist & possible
    metrics['recall'] = len(tpos) / len(possible)
    return metrics


def load_cfs_data(
    nermnl_jsonl: str,
    *,
    threshold_cfs: int,
) -> Tuple[Dict[str, str], Set[str], Dict[str, List[str]]]:
    tag_entity = {}
    possible_locator_set = defaultdict(int)
    remark = defaultdict(set)
    with open(nermnl_jsonl, 'r') as f:
        for line in f:
            label, data = json.loads(line)
            for t, e in data.items():
                tag_entity[t] = e
                remark[t].add(label)
            family = [t for t, e in data.items() if e == TagEntity.FAMILY]
            if len(family) > 0:
                for t, e in data.items():
                    if e in LOCATORS:
                        possible_locator_set[t] += 1
    # filter
    possible_locator_set = {
        t
        for t, c in possible_locator_set.items() if c >= threshold_cfs
    }
    # sort
    remark = {k: sorted(v) for k, v in remark.items()}
    return tag_entity, possible_locator_set, remark


@app.command(short_help='test incremental parsing for locator update')
def update(
    malgenome: bool = False,
    drebin: bool = False,
    threshold_cfs: int = 2,
    max_round: int = 3,
    dump: bool = False,
    lfs_mode: str = RunMode.UPDATE,
    verbose: int = 0,
    remain_inspect: int = 3,
):
    if malgenome:
        dataset = root / 'data/malgenome'
        vtapiv2_file = dataset / 'malgenome-vtapiv2.jsonl'
        nermnl_file = dataset / 'malgenome-nermnl.jsonl'
    elif drebin:
        dataset = root / 'data/drebin'
        vtapiv2_file = dataset / 'drebin-vtapiv2.jsonl'
        nermnl_file = dataset / 'drebin-nermnl.jsonl'
    else:
        print(f'[x] Assign a dataset first!')
        raise typer.Exit(-1)

    # load
    tag_entity, possible_locator_set, dataset_remark = load_cfs_data(
        nermnl_file,
        threshold_cfs=threshold_cfs,
    )
    family_truth_set = {
        t
        for t, e in tag_entity.items() if e == TagEntity.FAMILY
    }
    possible_locator_num = len(possible_locator_set)
    family_truth_num = len(family_truth_set)
    locator_truth_set = {t for t, e in tag_entity.items() if e in LOCATORS}
    # label
    label_engines = load_label_engines(vtapiv2_file)
    print(f'[*] {dataset.name} labels = {len(label_engines)}')
    # init vocabulary
    init_voc = Vocabulary([INIT_LOCATOR_VOC_FILE, INIT_MISC_VOC_FILE])
    # loop
    round_metrics = []
    round = 0
    round_updated_num = 1
    while round_updated_num > 0:
        round += 1
        if round > max_round:
            break
        round_updated_num = 0
        print(f'\n========== Locator update round {round} ==========')
        # start
        start_locator_set = set([t.name for t in init_voc.get_tags(LOCATORS)])
        start_family_set = set(
            [t.name for t in init_voc.get_tags([TagEntity.FAMILY])])
        remain_locator_set = possible_locator_set - start_locator_set
        remain_family_set = family_truth_set - start_family_set
        print('// initial vocabulary')
        print(f"[*] {init_voc}")
        print(f'// {dataset.name} summary')
        print(f'[*] locators = {possible_locator_num}')
        print(f'[*] families = {family_truth_num}')
        if verbose >= 1:
            inspect_remain_locators = {
                t: dataset_remark[t][:threshold_cfs]
                for i, t in enumerate(remain_locator_set) if i < remain_inspect
            }
            inspect_remain_families = {
                t: dataset_remark[t][:threshold_cfs]
                for i, t in enumerate(remain_family_set) if i < remain_inspect
            }
            print(
                f'[*] {remain_inspect} of {len(remain_locator_set)} remain locators:'
            )
            print(inspect_remain_locators)
            print(
                f'[*] {remain_inspect} of {len(remain_family_set)} remain families:'
            )
            print(inspect_remain_families)
        # updating
        print("// LFS-CFS loop until no new locator")
        init_voc = locator_incremental_update(
            label_engines,
            voc=init_voc,
            threshold_cfs=threshold_cfs,
            lfs_mode=lfs_mode,
            verbose=verbose,
        )
        # end
        end_locator_set = set([t.name for t in init_voc.get_tags(LOCATORS)])
        updated_locator_set = set([
            t.name for t in init_voc.get_tags(LOCATORS)
            if t.score == TagScore.UPDATED
        ])
        round_updated_set = end_locator_set - start_locator_set
        round_updated_num = len(round_updated_set)
        # metric
        print('// loop summary')
        print(f'[*] upated locators = {round_updated_num}')
        if verbose >= 1 and round_updated_num:
            inspect_updated_locators = {
                t: dataset_remark[t][:threshold_cfs]
                for t in round_updated_set
            }
            print(inspect_updated_locators)

        pre_rec = precision_recall(
            updated_locator_set,
            locator_truth_set,
            end_locator_set,
            possible_locator_set,
        )
        print(pre_rec)
        pre_rec['updated'] = round_updated_num
        round_metrics.append(pre_rec)

        # simulates manually verifying the update locator
        print(f'// imitating verification')
        for k, tag in init_voc.value.items():
            # only verify locators
            if tag.entity not in LOCATORS:
                continue
            # ignore old updated
            if tag.name in start_locator_set:
                continue
            # verify tag
            init_voc.update(
                k,
                entity=tag_entity[k],
                score=TagScore.UPDATED,
            )
            # verify remark
            if tag.remark is not None:
                remark = tag.remark.split('->')[0].strip()
                init_voc.update(
                    remark,
                    entity=tag_entity[remark],
                    score=TagScore.UPDATED,
                )
        # clean
        init_voc.value = {
            k: v
            for k, v in init_voc.value.items()
            if v.score in [TagScore.UPDATED, TagScore.CONFIRMED]
        }
        # dump
        if dump:
            init_voc.dump(LOCATORS, INIT_LOCATOR_VOC_FILE)
            init_voc.dump([TagEntity.MISC], INIT_MISC_VOC_FILE)
        # failed updated
        failed_update = possible_locator_set - set(
            [t.name for t in init_voc.get_tags(LOCATORS)])
        if verbose >= 2 and failed_update:
            print(f'[*] failed updated = {len(failed_update)}')
            print(failed_update)
        print('============================================')
    # report
    failed_update = possible_locator_set - set(
        [t.name for t in init_voc.get_tags(LOCATORS)])
    print(f'// report')
    if round <= max_round:
        print(f'[-] LIU finishes at round {round}')

    else:
        print(f'[-] LIU exceeds max round {max_round}')
    print(f'[-] threshold_cfs = {threshold_cfs} | lfs_mode = {lfs_mode}')
    print(
        f'[-] {dataset.name}: labels = {len(label_engines)} | locators = {len(possible_locator_set)}'
    )
    print(f'[*] failed updated = {len(failed_update)}')
    print('[*] metricss of each round: ')
    print(round_metrics)


@app.command(short_help='test CFS threshold')
def threshold(
    dataset: str = 'motif',
    max_threshold: int = 16,
    max_round: int = 3,
    lfs_mode: str = 'updating',
):
    nermnl_file = root / f'data/{dataset}/{dataset}-nermnl.jsonl'
    vtapiv2_file = root / f'data/{dataset}/{dataset}-vtapiv2.jsonl'
    # malware labels
    label_engines = load_label_engines(vtapiv2_file)
    print(f'[*] {dataset} labels = {len(label_engines)}')

    record = {}
    for threshold in range(2, max_threshold + 1):
        print(f'========== threshold_cfs = {threshold} ==========')
        # init vocabulary
        init_voc = Vocabulary([INIT_LOCATOR_VOC_FILE, INIT_MISC_VOC_FILE])
        # truth
        tag_entity, possible_locator_set, _ = load_cfs_data(
            nermnl_file,
            threshold_cfs=threshold,
        )
        locator_truth_set = {t for t, e in tag_entity.items() if e in LOCATORS}
        # loop
        round_metrics = []
        round = 0
        round_updated_num = 1
        while round_updated_num > 0:
            round += 1
            if round >= max_round:
                break
            round_updated_num = 0
            # start
            start_locator_set = set(
                [t.name for t in init_voc.get_tags(LOCATORS)])
            # updating
            init_voc = locator_incremental_update(
                label_engines,
                voc=init_voc,
                threshold_cfs=threshold,
                lfs_mode=lfs_mode,
            )
            # end
            end_locator_set = set(
                [t.name for t in init_voc.get_tags(LOCATORS)])
            updated_locator_set = set([
                t.name for t in init_voc.get_tags(LOCATORS)
                if t.score == TagScore.UPDATED
            ])
            round_updated_set = end_locator_set - start_locator_set
            round_updated_num = len(round_updated_set)
            # pr
            pre_rec = precision_recall(
                updated_locator_set,
                locator_truth_set,
                end_locator_set,
                possible_locator_set,
            )
            pre_rec['updated'] = round_updated_num
            round_metrics.append(pre_rec)

            # simulates manually verifying the update locator
            print(f'// imitating verification')
            for k, tag in init_voc.value.items():
                # ignore old updated
                if tag.name in start_locator_set:
                    continue
                # verify tag
                init_voc.update(
                    k,
                    entity=tag_entity[k],
                    score=TagScore.UPDATED,
                )
                # verify remark
                if tag.remark is not None:
                    remark = tag.remark.split('->')[0].strip()
                    init_voc.update(
                        remark,
                        entity=tag_entity[remark],
                        score=TagScore.UPDATED,
                    )
            # clean
            init_voc.value = {
                k: v
                for k, v in init_voc.value.items()
                if v.score in [TagScore.UPDATED, TagScore.CONFIRMED]
            }
        # report
        print(f'// report')
        if round < max_round:
            print(f'[-] LIU finishes at round {round}')

        else:
            print(f'[-] LIU exceeds max round {round}')
        print(f'[-] threshold_cfs = {threshold} | lfs_mode = {lfs_mode}')
        print(
            f'[-] {dataset}: labels = {len(label_engines)} | locators = {len(possible_locator_set)}'
        )
        print('[*] round_metricss of each round: ')
        print(round_metrics)
        record[threshold] = {
            'init': round_metrics[0],
            'final': round_metrics[-1]
        }
    # records
    print('[*] metrics of each threshold: ')
    print(record)
    with open(Path.cwd() / 'threshold-metirc.json', 'w') as f:
        json.dump(record, f)


def load_lfs_data(
    nermnl_jsonl: str,
    *,
    threshold_cfs: int,
) -> Tuple[Vocabulary, Dict[str, str]]:

    count = {k: defaultdict(int) for k in LOCATORS}
    label_family = {}
    with open(nermnl_jsonl, 'r') as f:
        for line in f:
            label, data = json.loads(line)
            label = label.strip().lower()
            family = [t for t, e in data.items() if e == TagEntity.FAMILY]
            if len(family) == 0:
                label_family[label] = None
            else:
                label_family[label] = family[-1]
                for t, e in data.items():
                    if e in count:
                        count[e][t] += 1

    voc = Vocabulary([INIT_LOCATOR_VOC_FILE, INIT_MISC_VOC_FILE])
    # Imitate CFS
    # tags with threshold_cfs >= 6 will be confirmed by the CFS
    for e, data in count.items():
        for t, c in data.items():
            if c >= threshold_cfs:
                voc.update(t, entity=e, score=TagScore.CONFIRMED)

    return voc, label_family


def print_error_table(
    data: List[Tuple],
    *,
    name='error',
):
    error_table = Table(title=name)
    column_style = {
        'engine': 'cyan',
        'label': 'cyan',
        'true_family': 'green',
        'parsed_family': 'red',
    }
    for c, s in column_style.items():
        error_table.add_column(c, style=s)

    for item in data:
        error_table.add_row(*item)
    print(error_table)


@app.command(short_help='test location first search for parsing')
def parse(
    malgenome: bool = False,
    drebin: bool = False,
    scoperr: bool = False,
    euperr: bool = False,
    cfs: int = 6,
    verbose: int = -1,
):
    if malgenome:
        dataset = root / 'data/malgenome'
        vtapiv2_file = dataset / 'malgenome-vtapiv2.jsonl'
        nermnl_file = dataset / 'malgenome-nermnl.jsonl'
        euphony_parsed_file = dataset / 'malgenome-euphony-parsed.json'
    elif drebin:
        dataset = root / 'data/drebin'
        vtapiv2_file = dataset / 'drebin-vtapiv2.jsonl'
        nermnl_file = dataset / 'drebin-nermnl.jsonl'
        euphony_parsed_file = dataset / 'drebin-euphony-parsed.json'
    else:
        print(f'[x] Assign a dataset first!')
        raise typer.Exit(-1)

    for pfile in [vtapiv2_file, nermnl_file, euphony_parsed_file]:
        if not pfile.exists():
            print(f'[x] {pfile.name} does not exists!')
            raise typer.Exit(-1)

    # load
    label_engines = load_label_engines(vtapiv2_file)
    voc, groundtruth = load_lfs_data(nermnl_file, threshold_cfs=cfs)
    with open(euphony_parsed_file, 'r') as f:
        euphony_result: Dict[str, str] = json.load(f)
    # tagclass
    parser = Parser(Tokenizer(), mode=RunMode.PARSE)
    results: Dict[str, ParseResult] = {}
    for label, engines in label_engines.items():
        data = parser.parse(
            label,
            engine=engines[0],
            voc=voc,
        )
        label_lower = label.strip().lower()
        family = None
        score = TagScore.UNKNOWN
        for r in data:
            if r.entity == TagEntity.FAMILY:
                family = r.tag
                score = r.score
                break

        if label_lower not in results:
            results[label_lower] = ParseResult(
                label,
                engines[0],
                family,
                score,
            )
        elif score > results[label_lower].score:
            results[label_lower] = ParseResult(
                label,
                engines[0],
                family,
                score,
            )
    # euphony scope acc
    scope_acc = defaultdict(list)
    eup1_tag0 = []
    scope_tag0 = []
    eup0 = []
    for label, family in euphony_result.items():
        # gt
        label = label.strip().lower()
        gt_fam = groundtruth[label]
        # tagclass
        parsed = results[label]
        label_origin = parsed.label
        engine = parsed.engine
        # acc
        eup = gt_fam == family
        tag = gt_fam == parsed.family
        scope_acc['euphony'].append(eup)
        scope_acc['tagclass'].append(tag)
        # eup0
        if not eup:
            eup0.append((engine, label_origin, gt_fam, family))
        # tag0
        if not tag:
            record = (engine, label_origin, gt_fam, parsed.family)
            scope_tag0.append(record)
            if eup:
                eup1_tag0.append(record)
    # all acc
    tagclass_acc = []
    tag0 = []
    for label, parsed in results.items():
        gt_fam = groundtruth[label]
        acc = gt_fam == parsed.family
        tagclass_acc.append(acc)
        if not acc:
            label_origin = parsed.label
            engine = parsed.engine
            tag0.append((engine, label_origin, gt_fam, parsed.family))
    # scope error
    if scoperr:
        if verbose == 0:
            print_error_table(
                scope_tag0,
                name='TagClass Error in the Scope of Euphony',
            )
            if euperr:
                print_error_table(
                    eup0,
                    name='Euphony Error',
                )
        elif verbose == 1:
            print_error_table(
                eup1_tag0,
                name='Euphony Success TagClass Error',
            )
    else:
        if verbose >= 0:
            print_error_table(tag0, name='TagClass Error')
    # summary
    # scope acc
    print(f'''[*] ============ Acc of Euphony scope ============ 
    {dataset.name} labels = {len(groundtruth)}
    Euphony scope = {len(euphony_result)}
    Euphony success but Tagclass failed = {len(eup1_tag0)}
    Tagclass failed in the Scope of Euphony = {len(scope_tag0)}
    Euphony Acc = {sum(scope_acc['euphony']) / len(scope_acc['euphony'])}
    Tagclass Acc = {sum(scope_acc['tagclass']) / len(scope_acc['tagclass'])}
    =============================================''')
    # all acc
    print(f'''[*] ============= Acc of all labels =============
    {dataset.name} labels = {len(groundtruth)}
    Tagclass failed  = {len(tag0)}
    Tagclass Acc = {sum(tagclass_acc) / len(tagclass_acc)}
    =============================================''')


if __name__ == '__main__':
    update(malgenome=True,
           drebin=False,
           threshold_cfs=2,
           max_round=5,
           dump=False,
           lfs_mode=RunMode.UPDATE,
           verbose=1)
