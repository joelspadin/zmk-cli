"""
Build matrix processing.
"""

import collections.abc
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

import dacite

from .repo import Repo
from .yaml import YAML


@dataclass
class BuildItem:
    """An item in the build matrix"""

    board: str
    shield: Optional[str] = None
    snippet: Optional[str] = None
    cmake_args: Optional[str] = None
    artifact_name: Optional[str] = None


@dataclass
class _BuildMatrixWrapper:
    include: list[BuildItem] = field(default_factory=list)


class BuildMatrix:
    """Interface to read and edit ZMK's build.yaml file"""

    _path: Path
    _yaml: YAML
    _data: Any

    @classmethod
    def from_repo(cls, repo: Repo):
        """Get the build matrix for a repo"""
        return cls(repo.build_matrix_path)

    def __init__(self, path: Path) -> None:
        self._path = path
        self._yaml = YAML(typ="rt")
        self._yaml.indent(mapping=2, sequence=4, offset=2)
        try:
            self._data = self._yaml.load(self._path)
        except FileNotFoundError:
            self._data = None

    def write(self):
        """Updated the YAML file, creating it if necessary"""
        self._yaml.dump(self._data, self._path)

    @property
    def path(self):
        """Path to the matrix's YAML file"""
        return self._path

    @property
    def include(self) -> list[BuildItem]:
        """List of build items in the matrix"""
        normalized = _keys_to_python(self._data)
        if not normalized:
            return []

        wrapper = dacite.from_dict(_BuildMatrixWrapper, normalized)
        return wrapper.include

    def has_item(self, item: BuildItem):
        """Get whether the matrix has a build item"""
        return item in self.include

    def add_items(self, items: Iterable[BuildItem]) -> bool:
        """
        Add build items to the matrix.

        Returns whether any items were added.
        """
        include = self.include
        items = [i for i in items if i not in include]

        if not items:
            return False

        if not self._data:
            self._data = self._yaml.map()

        if "include" not in self._data:
            self._data["include"] = self._yaml.seq()

        self._data["include"].extend([_to_yaml(i) for i in items])
        return True


def _keys_to_python(data: Any):
    """
    Fix any keys with hyphens to underscores so that dacite.from_dict() will
    work correctly.
    """

    def fix_key(key: str):
        return key.replace("-", "_")

    match data:
        case str():
            return data

        case collections.abc.Sequence():
            return [_keys_to_python(i) for i in data]

        case collections.abc.Mapping():
            return {fix_key(k): _keys_to_python(v) for k, v in data.items()}

        case _:
            return data


def _to_yaml(item: BuildItem):
    """
    Convert a BuildItem to a dict with keys changed back from underscores to hyphens.
    """

    def fix_key(key: str):
        return key.replace("_", "-")

    data = asdict(item)

    return {fix_key(k): v for k, v in data.items() if v is not None}
