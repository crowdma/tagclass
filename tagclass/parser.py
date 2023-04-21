from typing import List, Tuple

from dataclasses import dataclass
from tagclass.tokenizer import Tokenizer
from tagclass.common import Engine, Label
from tagclass.tag import (
    Vocabulary,
    TagEntity,
    LOCATORS,
    TagScore,
)


@dataclass
class Result:
    tag: str = None
    entity: str = None
    score: int = TagScore.UNKNOWN


def filepath_like(label: Label) -> bool:
    # \sav6\work_channel1_12\57745154
    # /sav6/work_channel1_12/57745154
    if label.count('/') > 2:
        return True
    if label.count('\\') > 0:
        return True

    return False


def is_valid_label(label: Label) -> bool:
    # check filepath-like
    if filepath_like(label):
        return False
    # others
    return True


def digit_ratio(tag: str) -> float:
    tag_len = len(tag)
    if tag_len == 0:
        return 1.0

    count = sum(c.isdigit() for c in tag)
    return count / tag_len


def is_valid_family(
    result: Result,
    label: str,
    engine: str,
) -> bool:
    '''A temporary patch'''
    # todo: add module to filter ``family''
    if result.score == TagScore.CONFIRMED:
        return True

    tag = result.tag
    # score
    if len(tag) <= 3:
        return False
    # 0. digit_ratio
    if digit_ratio(tag) >= 0.5:
        return False
    # 1. Tencet Title(4) end <Win64.Trojan.Inject.Eawu>
    if engine == 'Tencent' and len(tag) == 4:
        last_tag = label.rsplit('.', 1)[-1]
        if last_tag.istitle() and last_tag.lower() == tag:
            # from pathlib import Path
            # with open(Path.cwd() / '1-invalid.txt', 'a') as f:
            #     f.write(f'{tag} {normalize_label_name(label)} {result.entity}\n')
            return False
    # # 2. Cyren Uppercase <W32/Trojan.ZTSA-8671>
    # if engine in ['Cyren', 'Avira'] and tag.upper() in label:
    #     # last_tag = parsed.label.rsplit('.', 1)[-1]
    #     # if '-' in last_tag and last_tag.split('-')[-1].isdigit():
    #     # return False
    #     from pathlib import Path
    #     with open(Path.cwd() / '2-invalid.txt', 'a') as f:
    #         f.write(f'{tag} {normalize_label_name(label)} {result.entity}\n')
    #     return False
    # 3. Uppercase(4) end
    # LastUpper4Engines = ['Sophos', 'F-Prot']
    # if engine in LastUpper4Engines and len(tag) == 4:
    #     last_tag = label.rsplit('.', 1)[-1]
    #     if tag.upper() == last_tag:
    #         return False

    return True


class RunMode:
    PARSE = 'parsing'
    UPDATE = 'updating'


class Parser:
    def __init__(
        self,
        tokenizer: Tokenizer,
        mode: str = RunMode.PARSE,
    ):
        self.tokenizer = tokenizer
        self.mode = mode

    def cfs(
        self,
        engine: Engine,
        label: Label,
        voc: Vocabulary,
    ) -> Tuple[str, List[str]]:
        '''Cooccurence Fist Search
        search potential locator tags by <family, locator> cooccurence
        '''
        token_list = self.tokenizer.run(engine, label)
        for t in token_list:
            tag = voc.get(t)
            if tag.entity == TagEntity.FAMILY:
                return tag.name, [i for i in token_list if i != tag.name]
        return '', []

    def lfs(
        self,
        token_list: List[str],
        voc: Vocabulary,
    ) -> List[Result]:
        '''Location First Search
        search family tag in the context of locator tags.
        '''
        # query
        result_list: List[Result] = []
        inspect_list: List[Result] = []
        family_queried: List[Result] = []
        locator_num: int = 0
        for t in token_list:
            tag = voc.get(t)
            entity = tag.entity
            r = Result(tag.name, tag.entity, tag.score)
            result_list.append(r)
            if entity is None:
                inspect_list.append(r)
            elif entity in LOCATORS:
                inspect_list.append(r)
                locator_num += 1
            elif entity == TagEntity.FAMILY:
                family_queried.append(r)

        # hit family in the vocabulary
        family_score = TagScore.get(locator_num)
        if len(family_queried) > 0:
            for r in family_queried:
                r.score = max(r.score, family_score)
                voc.update(r.tag, score=r.score)
            return result_list
        # all locator
        if locator_num == len(inspect_list):
            return result_list
        # no locator
        if locator_num == 0:
            if self.mode == RunMode.PARSE and len(inspect_list):
                r: Result = [r for r in inspect_list if r.entity is None][0]
                r.entity = TagEntity.FAMILY
                r.score = TagScore.NO_LOCATOR_SEARCHED
                voc.update(r.tag, entity=r.entity, score=r.score)
            return result_list

        # location first search
        locations: List[int] = []
        unkowns: List[int] = []
        for i, r in enumerate(inspect_list):
            if r.entity in LOCATORS:
                locations.append(i)
            else:
                unkowns.append(i)
        first, last = locations[0], locations[-1]
        if len(inspect_list[first:last + 1]) == locator_num:
            # 1-continous
            loc = (first - 1) if (first - 1 >= 0) else (last + 1)
        else:
            # 2-discontinous
            loc = [i for i in range(first + 1, last) if i in unkowns][0]
        ignore_searched = (self.mode == RunMode.UPDATE) and (
            family_score <= TagScore.SINGLE_LOCATOR_SEARCHED)
        if not ignore_searched:
            r = inspect_list[loc]
            r.entity = TagEntity.FAMILY
            r.score = family_score
            voc.update(r.tag, entity=r.entity, score=r.score)
        return result_list

    def parse(
        self,
        label: Label,
        engine: Engine,
        voc: Vocabulary,
    ) -> List[Result]:
        if not is_valid_label(label):
            return []
        # tokenize
        token_list = self.tokenizer.run(engine, label)
        # location first search
        searched = self.lfs(token_list, voc)
        # check
        results = []
        for r in searched:
            if r.entity is None:
                continue
            if r.entity == TagEntity.FAMILY and not is_valid_family(
                    r, label, engine):
                voc.update(r.tag, entity=None, score=TagScore.CONFIRMED)
                continue
            results.append(r)
        return results