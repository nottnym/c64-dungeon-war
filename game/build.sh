#!/bin/bash
# Build Dungeon War (C#64): build/dungeon.prg + build/dungeon.d64
# Kompilátor: cs64build z repozitára Bruce Lee (tools/cs64build, stavia na C64U-Code.Shared).
set -e
cd "$(dirname "$0")"
mkdir -p build
CS64BUILD="../../Bruce Lee/tools/cs64build/bin/Release/net10.0/cs64build.dll"
dotnet "$CS64BUILD" dungeon.cs64 build/dungeon.prg --asm build/dungeon.asm \
    --d64 build/dungeon.d64 --diskname "DUNGEON WAR" --diskid DW --mainname "DUNGEON WAR"

# Krok 10: kód a konštanty musia skončiť pod obrazovkou $8400 (layout.cs64: A_CODE_TOP) – kompilátor to nekontroluje.
# Koniec sa berie z PRG: program je súvislý od $0801, medzera po charset $8800 je vyplnená nulami (review k10 č. 2).
python -I - <<'PY' || { rm -f build/dungeon.prg build/dungeon.d64; exit 1; }
import sys
d = open('build/dungeon.prg', 'rb').read()
base = d[0] | d[1] << 8
code = d[2:2 + 0x8400 - base]                   # $0801..$83FF
end = base + len(code.rstrip(bytes(1))) + 1        # +1: koncová nula posledného reťazca
tail = d[2 + 0x8400 - base:2 + 0x87E8 - base]   # obrazovka $8400..$87E7 musí byť v PRG prázdna
print(f'koniec kódu ${end:04X} (rezerva do $8400: {0x8400 - end} B)')
if end > 0x8400 or any(tail):
    print('CHYBA: kód zasahuje do obrazovky $8400 – build/dungeon.prg a .d64 zmazané', file=sys.stderr)
    sys.exit(1)
PY
