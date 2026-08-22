from __future__ import annotations

import hashlib
import random
from typing import Protocol, Sequence, TypeVar

T = TypeVar("T")


class RandomSource(Protocol):
    def random(self) -> float: ...
    def uniform(self, a: float, b: float) -> float: ...
    def choice(self, values: Sequence[T]) -> T: ...
    def randint(self, a: int, b: int) -> int: ...
    def sample(self, values: Sequence[T], count: int) -> list[T]: ...


class SeededRandom:
    def __init__(self, seed: int) -> None:
        self._generator = random.Random(seed)

    def random(self) -> float:
        return self._generator.random()

    def uniform(self, a: float, b: float) -> float:
        return self._generator.uniform(a, b)

    def choice(self, values: Sequence[T]) -> T:
        return self._generator.choice(list(values))

    def randint(self, a: int, b: int) -> int:
        return self._generator.randint(a, b)

    def sample(self, values: Sequence[T], count: int) -> list[T]:
        bounded_count = max(0, min(count, len(values)))
        return self._generator.sample(list(values), bounded_count)


class RandomStreams:
    def __init__(self, root_seed: int) -> None:
        self._root_seed = root_seed

    def stream(self, name: str) -> SeededRandom:
        digest = hashlib.sha256(f"{self._root_seed}:{name}".encode("utf-8")).digest()
        derived_seed = int.from_bytes(digest[:8], "big")
        return SeededRandom(derived_seed)
