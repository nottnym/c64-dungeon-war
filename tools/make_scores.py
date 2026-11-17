"""Predvolená tabuľka najvyšších skóre Dungeon War → game/assets/scores.bin (45 B).

5 záznamov po 9 B: 6 číslic skóre (0–9, najvyššia prvá) + 3 znaky mena v kódoch obrazovky (A = 1 … Z = 26, medzera 32).
Hra súbor "DW SCORES" po novom zázname prepíše (screens.cs64).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRIES = [(5000, 'DW '), (4000, 'DW '), (3000, 'DW '), (2000, 'DW '), (1000, 'DW ')]


def code(ch):
    return 32 if ch == ' ' else ord(ch) - ord('A') + 1


out = bytearray()
for score, name in ENTRIES:
    out += bytes(int(d) for d in f'{score:06d}')
    out += bytes(code(c) for c in name)
assert len(out) == 45
with open(os.path.join(HERE, '..', 'game', 'assets', 'scores.bin'), 'wb') as f:
    f.write(out)
print('scores.bin', len(out), 'B')
