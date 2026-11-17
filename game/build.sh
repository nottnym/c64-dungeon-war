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
python -I - <<'PY'
import re, sys
top = 0
for line in open('build/dungeon.labels', encoding='utf-8'):
    m = re.match(r'\$([0-9A-F]{4}) <cs64>::(\S+)', line)
    if m:
        a = int(m.group(1), 16)
        if 0x0801 <= a < 0x8800 and not m.group(2).startswith('Mux2_'):
            top = max(top, a)
# za posledným návestím môže byť ešte reťazec/tabuľka – preto rezerva 64 B
print(f'koniec kódu ~${top:04X} (rezerva do $8400: {0x8400 - top} B)')
if top >= 0x8400 - 64:
    print('CHYBA: kód zasahuje do obrazovky $8400', file=sys.stderr); sys.exit(1)
PY
