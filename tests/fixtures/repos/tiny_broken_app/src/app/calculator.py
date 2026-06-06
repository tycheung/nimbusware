"""Broken calculator fixture — add() returns wrong value on purpose."""


def add(a: int, b: int) -> int:
    return a + b + 1
