from typing import List, Dict, Set

from rich import print, progress
from collections import defaultdict

from tagclass.common import Label, Engine
from tagclass.tokenizer import Tokenizer
from tagclass.parser import Parser, RunMode
from tagclass.tag import (
    Vocabulary,
    TagScore,
    TagEntity,
    LOCATORS,
)


def cfs(
    label_engines: Dict[Label, Engine],
    parser: Parser,
    voc: Vocabulary,
    threshold_cfs: int,
    certs: Set[str] = None,
) -> int:
    start_locator_num = voc.count_tags(LOCATORS)
    # couting
    counter = defaultdict(int)
    remark = {}
    for label, engines in progress.track(
            label_engines.items(),
            total=len(label_engines),
            description='CFS...',
    ):
        family, result = parser.cfs(engines[0], label, voc)
        if not family:
            continue
        if len(result) == 0:
            continue
        # occurrence along with family tags
        for t in result:
            counter[t] += 1
            if t not in remark:
                remark[t] = f'{family} -> {label}'
    # updating
    for t, coocur in counter.items():
        if coocur < threshold_cfs:
            continue
        if voc.get(t).score in [TagScore.UPDATED, TagScore.CONFIRMED]:
            continue
        if certs is not None and t not in certs:
            continue

        voc.update(
            t,
            entity=TagEntity.BEHAVIOR,
            score=TagScore.UPDATED,
            remark=remark[t],
        )
    end_locator_num = voc.count_tags(LOCATORS)

    return end_locator_num - start_locator_num


def lfs(
    label_engines: Dict[Label, List[Engine]],
    parser: Parser,
    voc: Vocabulary,
    certs: Set[str] = None,
) -> int:
    start_family_num = voc.count_tags([TagEntity.FAMILY])
    for label, engines in progress.track(
            label_engines.items(),
            total=len(label_engines),
            description='LFS...',
    ):
        parser.parse(label, engines[0], voc)
    # certs
    if certs is not None:
        for t in voc.get_tags([TagEntity.FAMILY]):
            if t.name not in certs:
                t.entity = None
                t.score = TagScore.UNKNOWN
    end_family_num = voc.count_tags([TagEntity.FAMILY])
    return end_family_num - start_family_num


def locator_incremental_update(
    label_engines: Dict[Label, List[Engine]],
    voc: Vocabulary,
    threshold_cfs: int,
    lfs_mode: str = RunMode.UPDATE,
    verbose: int = 0,
    certs: Set[str] = None,
):
    tokenizer = Tokenizer()
    parser = Parser(tokenizer, mode=lfs_mode)
    # step
    step = 1
    new_loc_num = 1
    while new_loc_num:
        # === lfs ===
        if verbose:
            print(f'[-] ===== step {step} =====')
        new_family_num = lfs(label_engines=label_engines,
                             parser=parser,
                             voc=voc,
                             certs=certs)
        if verbose:
            print(f'[*] LFS: new family = {new_family_num}')
        # === cfs ===
        new_loc_num = cfs(label_engines=label_engines,
                          parser=parser,
                          voc=voc,
                          threshold_cfs=threshold_cfs,
                          certs=certs)
        if verbose:
            print(f'[*] CFS: new locator = {new_loc_num}')
        step += 1
        # clean
        for t in voc.get_tags([TagEntity.FAMILY]):
            if t.score != TagScore.CONFIRMED:
                t.update(entity=None, score=TagScore.UNKNOWN)
    # done
    return voc
