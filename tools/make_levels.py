"""Dungeon War – podlažia z tools/levels.txt → game/assets/levels.bin.

Podlažie = 66 B, bunka (x, y) na indexe y * 11 + x:
  bit 0 = stena vpravo, bit 1 = stena dole (posledný stĺpec/riadok = okraj),
  bit 2 = tunel vpravo (len x = 10), bit 3 = otvor do brány dole (len y = 5).
Ľavý a horný okraj je vždy stena; tunel vľavo je na rovnakom riadku ako vpravo (kontrola).
Kontroly: rozmery, okraj, súvislosť všetkých 66 buniek, tunely na oboch stranách, brány pod bunkami 0 a 10.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'levels.txt')
OUT = os.path.join(HERE, '..', 'game', 'assets', 'levels.bin')
W, H = 11, 6


def parse(name, rows):
    assert len(rows) == 2 * H + 1, f'{name}: {len(rows)} riadkov'
    rows = [r.ljust(2 * W + 1) for r in rows]
    for r in rows:
        assert len(r) == 2 * W + 1, f'{name}: riadok {r!r}'
    cells = [0] * (W * H)
    tun_l = [y for y in range(H) if rows[2 * y + 1][0] == 'T']
    tun_r = [y for y in range(H) if rows[2 * y + 1][2 * W] == 'T']
    assert tun_l == tun_r and len(tun_l) == 1, f'{name}: tunely {tun_l} {tun_r}'
    for y in range(H):
        assert rows[2 * y + 1][0] in '|T', f'{name}: ľavý okraj riadok {y}'
        for x in range(W):
            r = rows[2 * y + 1][2 * x + 2]
            d = rows[2 * y + 2][2 * x + 1]
            v = 0
            if r in '|T': v |= 1
            if r == 'T': v |= 4
            if d in '-G': v |= 2
            if d == 'G': v |= 8
            if x == W - 1: assert r in '|T', f'{name}: pravý okraj riadok {y}'
            if y == H - 1: assert d in '-G', f'{name}: spodný okraj stĺpec {x}'
            cells[y * W + x] = v
    for x in range(W):
        assert rows[0][2 * x + 1] == '-', f'{name}: horný okraj stĺpec {x}'
    gates = [x for x in range(W) if cells[(H - 1) * W + x] & 8]
    assert gates == [0, W - 1], f'{name}: brány {gates}'
    # súvislosť (tunely a brány sa nepočítajú)
    seen, todo = {0}, [0]
    while todo:
        i = todo.pop(); x, y = i % W, i // W
        nb = []
        if x < W - 1 and not cells[i] & 1: nb.append(i + 1)
        if x > 0 and not cells[i - 1] & 1: nb.append(i - 1)
        if y < H - 1 and not cells[i] & 2: nb.append(i + W)
        if y > 0 and not cells[i - W] & 2: nb.append(i - W)
        for j in nb:
            if j not in seen: seen.add(j); todo.append(j)
    assert len(seen) == W * H, f'{name}: nesúvislé, nedostupné bunky {sorted(set(range(W * H)) - seen)}'
    return bytes(cells)


levels, names, cur, rows = [], [], None, []
for line in open(SRC, encoding='utf-8'):
    line = line.rstrip('\n')
    if line.startswith('#'):
        continue
    if line.startswith('= '):
        if cur: levels.append(parse(cur, rows))
        cur, rows = line[2:].strip(), []
        names.append(cur)
    elif cur is not None and line.strip():
        rows.append(line)
if cur: levels.append(parse(cur, rows))
open(OUT, 'wb').write(b''.join(levels))
print(f'levels.bin: {len(levels)} podlaží ({len(levels) * W * H} B): ' + ', '.join(names))
