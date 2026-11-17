"""Parse menu input like '1,4,7' or '3-10' into album numbers."""
from __future__ import annotations


def parse_selection(text: str, total: int) -> list[int]:
    picked: set[int] = set()
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            lo, _, hi = part.partition("-")
            if not (lo.isdigit() and hi.isdigit()):
                raise ValueError(f"can't read '{part}'")
            lo, hi = sorted((int(lo), int(hi)))
            numbers = range(lo, hi + 1)
        elif part.isdigit():
            numbers = [int(part)]
        else:
            raise ValueError(f"can't read '{part}'")
        for n in numbers:
            if n < 1 or n > total:
                raise ValueError(f"{n} is out of range (1-{total})")
            picked.add(n)
    if not picked:
        raise ValueError("nothing selected")
    return sorted(picked)
