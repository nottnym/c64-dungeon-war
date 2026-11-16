#!/bin/bash
# Build Dungeon War (C#64): build/dungeon.prg + build/dungeon.d64
# Kompilátor: cs64build z repozitára Bruce Lee (tools/cs64build, stavia na C64U-Code.Shared).
set -e
cd "$(dirname "$0")"
mkdir -p build
CS64BUILD="../../Bruce Lee/tools/cs64build/bin/Release/net10.0/cs64build.dll"
dotnet "$CS64BUILD" dungeon.cs64 build/dungeon.prg --asm build/dungeon.asm \
    --d64 build/dungeon.d64 --diskname "DUNGEON WAR" --diskid DW --mainname "DUNGEON WAR"
