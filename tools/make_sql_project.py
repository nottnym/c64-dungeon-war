"""Generátor SQL skriptu: projekt „Dungeon War“ v databáze C64U Code z aktuálneho game/.

Zdrojové súbory sa odvodia z direktív `uses` od game/dungeon.cs64, dátové kúsky z odkazov "assets/<meno>"
(includeAt, place) – obsah je game/assets/<meno>.bin.

Skript je opakovateľný a nič nemaže:
  * projekt (hľadá sa podľa názvu) chýba → vloží ho aj s nastaveniami disku (voliteľne s pevným ID),
  * existuje → položky s iným obsahom aktualizuje, chýbajúce vloží; ostatné položky a projekty nechá tak.

Použitie:
  python tools/make_sql_project.py mssql out.sql            # SQL Server (sqlcmd -i out.sql, súbor v UTF-16)
  python tools/make_sql_project.py pg out.sql [--id 1]      # PostgreSQL (psql -v ON_ERROR_STOP=1 -f out.sql)

Voľby: --id N (ID nového projektu; pri PostgreSQL sa potom posunie sekvencia), --user GUID (vlastník; predvolene Admin).
"""
import argparse
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.join(HERE, '..', 'game')
MAIN = 'dungeon.cs64'
NAME = 'Dungeon War'
DESCRIPTION = 'Dungeon War – pôvodná bludisková strieľačka v C#64 (test náročnej hry), docs/DungeonWar-design.html.'
DISK_NAME, DISK_ID, MAIN_FILE = 'DUNGEON WAR', 'DW', 'DUNGEON WAR'
ADMIN = '2ED27B6A-557C-4E04-BAE8-FF94B9A3305C'
CS64, BIN, SIDTRACK = 192, 28, 188   # CodelistValue: typ položky C# 64, Binárne dáta, GT2 skladba
MUSIC_BASE = 0xB000          # báza GT2 hudby (tools/make_music: MUSIC_BASE, sound.cs64: A_MUSIC)
START = {}                   # path → CommonStartAddress (len SIDTRACK)


def read(path):
    return open(path, 'rb').read()


def collect_items():
    """[(path, typ, bytes)] – zdroje v poradí uses (hlavný prvý), potom dátové kúsky podľa mena."""
    sources, todo = [], [MAIN]
    while todo:
        name = todo.pop(0)
        if name in sources:
            continue
        sources.append(name)
        text = read(os.path.join(GAME, name)).decode('utf-8')
        todo += re.findall(r'^\s*uses\s+"([^"]+)"', text, re.M)
    items = []
    for name in sources:
        data = read(os.path.join(GAME, name))
        assert not data.startswith(b'\xef\xbb\xbf'), f'{name}: BOM'
        items.append((name, CS64, data))
    text = ''.join(read(os.path.join(GAME, n)).decode('utf-8') for n in sources)
    for asset in sorted(set(re.findall(r'"(assets/[A-Za-z0-9_]+)"', text))):
        # GT2 skladba (game/assets/<meno>.sng): položka SIDTRACK s obsahom .sng a bázou MUSIC_BASE – C64U Code ju
        # pri preklade zbalí prehrávačom na túto bázu; lokálny cs64build použije zbalené <meno>.bin.
        sng = os.path.join(GAME, asset + '.sng')
        if os.path.exists(sng):
            items.append((asset, SIDTRACK, read(sng)))
            START[asset] = MUSIC_BASE
        else:
            items.append((asset, BIN, read(os.path.join(GAME, asset + '.bin'))))
    return items


def mssql(items, pid, user):
    s = lambda v: 'NULL' if v is None else "N'" + v.replace("'", "''") + "'"
    out = ['SET NOCOUNT ON;', 'SET XACT_ABORT ON;', 'BEGIN TRANSACTION;',
           'DECLARE @p int, @n int = 0, @new int = 0;',
           f'SELECT @p = Id FROM Project WHERE Name = {s(NAME)};',
           'IF @p IS NULL BEGIN']
    cols = ('Name, Description, StartAddress, StartRoutine, CreatedDate, CreatedById, Obsolete, IsPublic, PackOutput, '
            'DiskName, DiskId, MainFileName')
    vals = (f"{s(NAME)}, {s(DESCRIPTION)}, NULL, {s(MAIN)}, SYSDATETIME(), '{user}', 0, 0, 0, "
            f"{s(DISK_NAME)}, {s(DISK_ID)}, {s(MAIN_FILE)}")
    if pid is not None:
        out += [f'    IF EXISTS (SELECT 1 FROM Project WHERE Id = {pid}) '
                f"BEGIN RAISERROR('ID {pid} je obsadené iným projektom.', 16, 1); RETURN; END;",
                '    SET IDENTITY_INSERT Project ON;',
                f'    INSERT INTO Project (Id, {cols}) VALUES ({pid}, {vals});',
                '    SET IDENTITY_INSERT Project OFF;', f'    SET @p = {pid};']
    else:
        out += [f'    INSERT INTO Project ({cols}) VALUES ({vals});', '    SET @p = SCOPE_IDENTITY();']
    out += ['    SET @new = 1;', 'END;']
    for path, typ, data in items:
        h = '0x' + data.hex().upper()
        st = START.get(path)
        st = 'NULL' if st is None else str(st)
        out += [f'UPDATE ProjectItem SET Content = {h}, CommonStartAddress = {st}, ChangedDate = SYSDATETIME(), '
                f'ChangedById = \'{user}\' '
                f'WHERE ProjectId = @p AND Path = {s(path)} AND SourceTypeId = {typ} '
                f'AND (Content <> {h} OR ISNULL(CommonStartAddress, -1) <> ISNULL({st}, -1)); '
                'SET @n = @n + @@ROWCOUNT;',
                f'IF NOT EXISTS (SELECT 1 FROM ProjectItem WHERE ProjectId = @p AND Path = {s(path)}) BEGIN '
                'INSERT INTO ProjectItem (ProjectId, Path, SourceTypeId, Content, CommonStartAddress, CreatedDate, '
                f"CreatedById, Obsolete) VALUES (@p, {s(path)}, {typ}, {h}, {st}, SYSDATETIME(), '{user}', 0); "
                'SET @n = @n + 1; END;']
    out += ['COMMIT TRANSACTION;',
            "SELECT 'PROJECT_ID=' + CAST(@p AS varchar(10)) + ' NEW=' + CAST(@new AS varchar(1)) "
            "+ ' CHANGED_ITEMS=' + CAST(@n AS varchar(10));"]
    return '\n'.join(out) + '\n', 'utf-16'


def pg(items, pid, user):
    s = lambda v: 'NULL' if v is None else "'" + v.replace("'", "''") + "'"
    u = user.lower()
    out = ['\\set ON_ERROR_STOP on', 'BEGIN;', 'DO $bl$', 'DECLARE', '    p integer;', '    n integer := 0;',
           '    c integer;', '    is_new boolean := false;', 'BEGIN',
           f'    SELECT "Id" INTO p FROM "Project" WHERE "Name" = {s(NAME)};', '    IF p IS NULL THEN']
    cols = ('"Name", "Description", "StartAddress", "StartRoutine", "CreatedDate", "CreatedById", "Obsolete", '
            '"IsPublic", "PackOutput", "DiskName", "DiskId", "MainFileName"')
    vals = (f"{s(NAME)}, {s(DESCRIPTION)}, NULL, {s(MAIN)}, localtimestamp, '{u}', false, false, false, "
            f"{s(DISK_NAME)}, {s(DISK_ID)}, {s(MAIN_FILE)}")
    if pid is not None:
        out += [f'        IF EXISTS (SELECT 1 FROM "Project" WHERE "Id" = {pid}) THEN '
                f"RAISE EXCEPTION 'ID {pid} je obsadené iným projektom.'; END IF;",
                f'        INSERT INTO "Project" ("Id", {cols}) VALUES ({pid}, {vals});', f'        p := {pid};',
                # identita BY DEFAULT: po vložení s explicitným ID posunúť sekvenciu, nech ďalší projekt nekoliduje
                '''        PERFORM setval(pg_get_serial_sequence('"Project"', 'Id'), (SELECT max("Id") FROM "Project"));''']
    else:
        out += [f'        INSERT INTO "Project" ({cols}) VALUES ({vals}) RETURNING "Id" INTO p;']
    out += ['        is_new := true;', '    END IF;']
    for path, typ, data in items:
        h = f"'\\x{data.hex()}'::bytea"
        st = START.get(path)
        st = 'NULL' if st is None else str(st)
        out += [f'    UPDATE "ProjectItem" SET "Content" = {h}, "CommonStartAddress" = {st}, '
                f'"ChangedDate" = localtimestamp, "ChangedById" = \'{u}\' '
                f'WHERE "ProjectId" = p AND "Path" = {s(path)} AND "SourceTypeId" = {typ} '
                f'AND ("Content" IS DISTINCT FROM {h} OR "CommonStartAddress" IS DISTINCT FROM {st});',
                '    GET DIAGNOSTICS c = ROW_COUNT; n := n + c;',
                f'    IF NOT EXISTS (SELECT 1 FROM "ProjectItem" WHERE "ProjectId" = p AND "Path" = {s(path)}) THEN',
                '        INSERT INTO "ProjectItem" ("ProjectId", "Path", "SourceTypeId", "Content", '
                '"CommonStartAddress", "CreatedDate", "CreatedById", "Obsolete") '
                f'VALUES (p, {s(path)}, {typ}, {h}, {st}, localtimestamp, \'{u}\', false);',
                '        n := n + 1;', '    END IF;']
    out += ["    RAISE NOTICE 'PROJECT_ID=% NEW=% CHANGED_ITEMS=%', p, is_new, n;", 'END', '$bl$;', 'COMMIT;']
    return '\n'.join(out) + '\n', 'utf-8'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('dialect', choices=['mssql', 'pg'])
    ap.add_argument('out')
    ap.add_argument('--id', type=int, help='ID nového projektu (len ak projekt ešte neexistuje)')
    ap.add_argument('--user', default=ADMIN, help='GUID vlastníka (predvolene Admin)')
    a = ap.parse_args()
    items = collect_items()
    text, enc = (mssql if a.dialect == 'mssql' else pg)(items, a.id, a.user)
    open(a.out, 'w', encoding=enc, newline='\n').write(text)
    print(f'{a.out}: {len(items)} položiek ({sum(t == CS64 for _, t, _ in items)} CS64, '
          f'{sum(t == BIN for _, t, _ in items)} BIN, {sum(t == SIDTRACK for _, t, _ in items)} SIDTRACK)')


if __name__ == '__main__':
    main()
