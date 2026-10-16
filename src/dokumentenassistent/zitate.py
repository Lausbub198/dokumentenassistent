"""Exact, context-bound citation groups. Unknown or ambiguous groups fail closed."""
from functools import lru_cache
from unicodedata import normalize


def zitatgruppen(text: str, erlaubte_ids):
    """Yield (start, end, ids) for non-nested, uniquely parsed bracket groups.

    IDs may themselves contain commas. Never split filenames on commas blindly.
    An invalid member rejects the entire group, not other independent groups.
    """
    # Keep every original identity, including canonical collisions. Two IDs with
    # the same NFC spelling produce two parses and therefore fail closed.
    ids = tuple((normalize('NFC', id_), id_) for id_ in
                sorted(set(erlaubte_ids), key=lambda s: (-len(s), s)))

    def parse(inhalt):
        inhalt = normalize('NFC', inhalt)
        @lru_cache(None)
        def suffix(pos):
            solutions = []
            for spelling, id_ in ids:
                if not inhalt.startswith(spelling, pos):
                    continue
                end = pos + len(spelling)
                if end == len(inhalt):
                    solutions.append((id_,))
                elif inhalt[end] == ',':
                    following = end + 1
                    while following < len(inhalt) and inhalt[following].isspace():
                        following += 1
                    for rest in suffix(following):
                        solutions.append((id_,) + rest)
                if len(solutions) > 1:
                    return tuple(solutions[:2])
            return tuple(solutions)

        solutions = suffix(0)
        return solutions[0] if len(solutions) == 1 else ()

    depth, start, nested = 0, 0, False
    for pos, char in enumerate(text):
        if char == '[':
            if depth == 0:
                start, nested = pos, False
            else:
                nested = True
            depth += 1
        elif char == ']' and depth:
            depth -= 1
            if depth == 0 and not nested:
                group = parse(text[start + 1:pos])
                if group:
                    yield start, pos + 1, group
