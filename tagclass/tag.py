from __future__ import annotations
from typing import Dict, List, Optional

import sys
import toml
from pathlib import Path
from collections import Counter


class TagEntity:
    # parsing
    BEHAVIOR = 'behavior'
    PLATFORM = 'platform'
    FAMILY = 'family'
    MISC = 'misc'
    OUTSIDE = 'outside'

    @classmethod
    def keys(cls) -> List[str]:
        return [v for k, v in cls.__dict__.items() if k.isupper()]


LOCATORS = [TagEntity.BEHAVIOR, TagEntity.PLATFORM]


class TagScore:
    '''[min, max] = [-1, 10]'''
    UNKNOWN = 0
    NO_LOCATOR_SEARCHED = 5
    SINGLE_LOCATOR_SEARCHED = 6
    LOCATORS_SEARCHED = 8
    UPDATED = 9
    CONFIRMED = 10

    @classmethod
    def get(cls, locator_num: int) -> int:
        if locator_num == 0:
            score = cls.NO_LOCATOR_SEARCHED
        elif locator_num == 1:
            score = cls.SINGLE_LOCATOR_SEARCHED
        elif locator_num >= 2:
            score = cls.LOCATORS_SEARCHED
        else:
            score = cls.UNKNOWN
        return score


class TagPath:
    GENERIC = 'generic'
    PACKERIC = 'packeric'


class Tag:
    __slots__ = [
        'name',
        'entity',
        'path',
        'abspath',
        'uuid',
        'score',
        'remark',
    ]

    def __init__(
        self,
        name: str,
        *,
        entity: Optional[str] = None,
        path: Optional[str] = None,
        uuid: Optional[str] = None,
        score: int = TagScore.UNKNOWN,
        remark: Optional[str] = None,
    ):
        self.name = name
        self.entity = entity
        self.path = path
        self.uuid = uuid if uuid is not None else name
        self.score = score
        self.remark = remark
        self.refresh_abspath()

    def refresh_abspath(self) -> None:
        # abspath
        entity = self.entity if self.entity is not None else 'None'
        path = self.path if self.path is not None else ''
        self.abspath = Path('/').joinpath(entity, path, self.uuid)

    def set_entity(self, entity: str) -> None:
        self.entity = entity
        self.refresh_abspath()

    def set_path(self, path: str) -> None:
        self.path = path
        self.refresh_abspath()

    def __hash__(self) -> int:
        return hash(self.name)

    def __str__(self) -> str:
        return f"Tag(name={self.name}, abspath={self.abspath}, score={self.score})"

    def __repr__(self) -> str:
        return str(self)

    def generic(self) -> bool:
        if TagPath.GENERIC in self.abspath.parts:
            return True
        else:
            return False

    def packeric(self) -> bool:
        if TagPath.PACKERIC in self.abspath.parts:
            return True
        else:
            return False

    def genpackeric(self) -> bool:
        if self.generic() or self.packeric():
            return True
        return False

    def unknown(self) -> bool:
        return self.score == TagScore.UNKNOWN

    def confirmed(self) -> bool:
        return self.score == TagScore.CONFIRMED

    def update(self, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.refresh_abspath()

    def asdict(self) -> Dict[str, str]:
        return {k: getattr(self, k) for k in self.__slots__}

    def dump(self) -> Dict[str, str]:
        ignore_keys = ['name', 'abspath']
        if self.name == self.uuid:
            ignore_keys.append('uuid')
        return {
            k: v
            for k, v in self.asdict().items() if v and k not in ignore_keys
        }


def load_voc(
    voc_file_list: List[Path],
    *,
    unconfirmed_ok: bool = False,
) -> Dict[str, Tag]:
    voc = {}
    for voc_file in voc_file_list:
        with open(voc_file, "r") as f:
            data = toml.load(f)
        for k, v in data.items():
            tag = Tag(k, **v)
            if tag.score != TagScore.CONFIRMED:
                if not unconfirmed_ok:
                    print(f"[x] {tag} is not confirmed")
                    sys.exit(-1)
                else:
                    continue
            if tag.name not in voc:
                voc[tag.name] = tag
            else:
                exist = voc[tag.name]
                print(f"[x] duplicate {tag} | {exist}")
                sys.exit(-1)
    return voc


def dump_voc(
    tag_dict: Dict[str, Tag],
    entity_list: List[str],
    voc_file: Path,
    *,
    ignore_unknown=True,
    sort: bool = False,
) -> None:
    data = {}
    for k, v in tag_dict.items():
        if v.entity not in entity_list:
            continue
        if ignore_unknown and v.score == TagScore.UNKNOWN:
            continue
        data[k] = v.dump()
    if sort:
        data = {
            k: v
            for k, v in sorted(
                data.items(),
                key=lambda x: [x[1]['entity'], x[0]],
            )
        }
    with open(voc_file, "w") as f:
        toml.dump(data, f)


def list_voc(tag_dict: Dict[str, Tag]) -> Dict[str, int]:
    return dict(Counter([t.entity for _, t in tag_dict.items()]))


class Vocabulary:
    '''Dict[str, Tag]'''
    __slots__ = ['value']

    def __init__(
        self,
        voc_files: List[Path] = None,
        *,
        unconfirmed_ok: bool = False,
    ) -> None:
        if voc_files is None:
            self.value = {}
        else:
            self.value = load_voc(
                voc_files,
                unconfirmed_ok=unconfirmed_ok,
            )

    def __len__(self):
        return len(self.value)

    def __getitem__(self, name: str) -> Tag:
        return self.value[name]

    def __repr__(self) -> str:
        return f"Vocabulary : {list_voc(self.value)}"

    def __str__(self) -> str:
        return f"Vocabulary : {list_voc(self.value)}"

    def hit(self, name: str) -> bool:
        return name in self.value

    def get(self, name: str) -> Tag:
        if name in self.value:
            return self.value[name]
        # not create
        return Tag(name)

    def get_or_create(self, name: str) -> Tag:
        if name in self.value:
            return self.value[name]
        # create
        return self.add(name)

    def add(self, name: str, **kwargs) -> Tag:
        t = Tag(name, **kwargs)
        self.value[name] = t
        return t

    def update(self, name: str, **kwargs) -> Tag:
        # add not exist
        if name not in self.value:
            return self.add(name, **kwargs)
        # exist
        t = self.value[name]
        # prohibit update confirmed
        if t.score == TagScore.CONFIRMED:
            return t
        # update
        if kwargs.get('score', TagScore.UNKNOWN) >= t.score:
            t.update(**kwargs)
        return t

    def get_tags(self, entities: List[str]) -> List[Tag]:
        return [t for _, t in self.value.items() if t.entity in entities]

    def count_tags(self, entities: List[str]) -> int:
        return len(self.get_tags(entities))

    def dump(
        self,
        entity_list: List[str],
        voc_file: Path,
        *,
        sort: bool = False,
        ignore_unknown: bool = True,
    ) -> None:
        dump_voc(
            self.value,
            entity_list,
            voc_file,
            sort=sort,
            ignore_unknown=ignore_unknown,
        )
