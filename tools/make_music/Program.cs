// make_music: hudba Dungeon War (GoatTracker 2) – prvá verzia od Clauda (dizajn kap. 8 a 18).
//
// Skladba sa skladá v kóde nižšie (nástroje, tabuľky, patterny ako text) cez model SidSong z C64U-Code.Shared.
// Výstupy:
//   game/assets/music.sng  – natívny GT2 .sng (GTS5) → položka SIDTRACK "assets/music" v C64U Code (dá sa upraviť v SID trackeri)
//   game/assets/music.bin  – zbalený prehrávač + dáta na MUSIC_BASE (init = báza, play = báza + 3) pre lokálny cs64build
//   game/build/music.sid   – PSID na vypočutie mimo hry
//
// Subtunes: 0 = titulka (slučka), 1 = znelka začiatku podlažia (~1,6 s, potom ticho),
//           2 = koniec hry (~3 s, potom ticho), 3 = ticho.
// Zápis riadku patternu: "A-4:1" = nota (C-0 … B-7, krížik "C#4") s nástrojom 1, "." = nič, "=" = KEYOFF.
using C64U_Code.Shared.Sid.Tracker;

const int MUSIC_BASE = 0xB000;          // dungeon.cs64: includeAt(A_MUSIC, "assets/music")
const byte REST = 0xBD, KEYOFF = 0xBE;

string root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
if (args.Length > 0) root = Path.GetFullPath(args[0]);
string assets = Path.Combine(root, "game", "assets");
string build = Path.Combine(root, "game", "build");

var song = new SidSong { Name = "Dungeon War", Author = "Claude", Copyright = "2026" };

// --- nástroje (1-based) ---
// gatetimer $02 + firstwave $09 = štandardný hard restart GT2
Instrument Ins(string name, byte ad, byte sr, byte wave, byte pulse = 0) =>
    new() { Name = name, AttackDecay = ad, SustainRelease = sr, WaveTablePtr = wave, PulseTablePtr = pulse, GateTimer = 0x02, FirstWave = 0x09 };

// Wave tabuľka (left = priebeh, right = nota: $00 relatívne 0, $80+n absolútne; $FF = skok, right 0 = koniec)
var wave = song.Tables[0].Rows;
var pulse = song.Tables[1].Rows;
byte W(params (byte, byte)[] rows) { byte at = (byte)(wave.Count + 1); wave.AddRange(rows); return at; }
byte P(params (byte, byte)[] rows) { byte at = (byte)(pulse.Count + 1); pulse.AddRange(rows); return at; }

byte wPulse = W((0x41, 0x00), (0xFF, 0x00));
byte wSaw = W((0x21, 0x00), (0xFF, 0x00));
byte wTri = W((0x11, 0x00), (0xFF, 0x00));
byte wSnare = W((0x81, 0xCC), (0x41, 0xA8), (0x81, 0xC4), (0xFF, 0x00));
byte wKick = W((0x81, 0xB8), (0x11, 0xA4), (0x11, 0x9C), (0x11, 0x94), (0x11, 0x8C), (0xFF, 0x00));
byte wHat = W((0x81, 0xDC), (0xFF, 0x00));
// pulse: nastav $0800, potom pomalá modulácia tam a späť
byte pLead = P((0x88, 0x00), (0x40, 0x10), (0x40, 0xF0), (0xFF, 0x02));
byte pBass = P((0x84, 0x00), (0xFF, 0x00));

song.Instruments.Add(Ins("Lead", 0x09, 0xA8, wPulse, pLead));   // 1
song.Instruments.Add(Ins("Bass", 0x08, 0x89, wSaw));            // 2
song.Instruments.Add(Ins("Snare", 0x00, 0xA9, wSnare, pBass));  // 3
song.Instruments.Add(Ins("Kick", 0x00, 0xA8, wKick));           // 4
song.Instruments.Add(Ins("Hat", 0x00, 0x60, wHat));             // 5
song.Instruments.Add(Ins("Pad", 0x48, 0x8A, wTri));             // 6

// --- patterny ---
var names = new Dictionary<string, byte>();
byte Pat(string name, string text, int defaultIns = 0)
{
    var p = new Pattern();
    foreach (var tok in text.Split(' ', StringSplitOptions.RemoveEmptyEntries))
    {
        if (tok == ".") { p.Rows.Add(new PatternRow { Note = REST }); continue; }
        if (tok == "=") { p.Rows.Add(new PatternRow { Note = KEYOFF }); continue; }
        var parts = tok.Split(':');
        int ins = parts.Length > 1 ? int.Parse(parts[1]) : defaultIns;
        p.Rows.Add(new PatternRow { Note = Note(parts[0]), Instrument = (byte)ins });
    }
    if (p.Rows.Count is 0 or > SidSong.MaxPatternRows) throw new Exception($"pattern {name}: {p.Rows.Count} riadkov");
    names[name] = (byte)song.Patterns.Count;
    song.Patterns.Add(p);
    return names[name];
}

static byte Note(string s)
{
    string[] n = { "C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-" };
    int semi = Array.IndexOf(n, s[..2].ToUpperInvariant());
    int oct = s[2] - '0';
    if (semi < 0 || oct < 0 || oct > 7) throw new Exception("zlá nota " + s);
    return (byte)(0x60 + oct * 12 + semi);
}

byte silent = Pat("silent", "= . . .");

// Titulka: a mol, 8 taktov po 16 riadkov (16-tiny), tempo 5 → 1,6 s na takt
string[] lead =
{
    "A-4 . . . C-5 . . . E-5 . . . D-5 . C-5 .",
    "C-5 . . . A-4 . . . F-4 . . . A-4 . . .",
    "B-4 . . . D-5 . . . G-5 . . . F-5 . E-5 .",
    "E-5 . . . . . . . G#4 . . . B-4 . . .",
    "A-4 . C-5 . E-5 . A-5 . G-5 . E-5 . C-5 . E-5 .",
    "F-5 . . . E-5 . . . D-5 . . . C-5 . . .",
    "D-5 . . . B-4 . . . G-4 . . . B-4 . D-5 .",
    "E-5 . . . . . . . = . . . . . . .",
};
string[] bass =
{
    "A-2 . A-2 . A-3 . A-2 . A-2 . A-2 . A-3 . G-2 .",
    "F-2 . F-2 . F-3 . F-2 . F-2 . F-2 . F-3 . E-2 .",
    "G-2 . G-2 . G-3 . G-2 . G-2 . G-2 . G-3 . G-2 .",
    "E-2 . E-2 . E-3 . E-2 . E-2 . E-2 . G#2 . B-2 .",
};
var leadP = lead.Select((t, i) => Pat("lead" + i, t, 1)).ToArray();
var bassP = bass.Select((t, i) => Pat("bass" + i, t, 2)).ToArray();
byte drums = Pat("drums", "C-4:4 . C-6:5 . C-5:3 . C-6:5 . C-4:4 . C-4:4 . C-5:3 . C-6:5 .");
byte drumsFill = Pat("drumsFill", "C-4:4 . C-6:5 . C-5:3 . C-6:5 . C-5:3 . C-5:3 C-5:3 . C-5:3 . C-5:3 C-5:3");

const byte LOOP = 0xFF;
song.Subtunes.Add(new Subtune { Orderlists = {
    [0] = [.. leadP, LOOP, 0],
    [1] = [bassP[0], bassP[1], bassP[2], bassP[3], bassP[0], bassP[1], bassP[2], bassP[3], LOOP, 0],
    [2] = [drums, drums, drums, drumsFill, drums, drums, drums, drumsFill, LOOP, 0],
} });

// Znelka podlažia (~1,6 s, intro hry trvá 2 s), potom ticho
byte jLead = Pat("jingleLead", "E-4 . A-4 . C-5 . E-5 . A-5 . . . . . . =", 1);
byte jBass = Pat("jingleBass", "A-2 . . . E-3 . . . A-3 . . . . . . =", 2);
byte jDrum = Pat("jingleDrum", "C-4:4 . . . C-4:4 . . . C-5:3 . C-5:3 . C-5:3 . . .");
song.Subtunes.Add(new Subtune { Orderlists = {
    [0] = [jLead, silent, LOOP, 1], [1] = [jBass, silent, LOOP, 1], [2] = [jDrum, silent, LOOP, 1],
} });

// Koniec hry (~3,2 s), potom ticho
byte oLead = Pat("overLead", "E-5 . . . D-5 . . . C-5 . . . B-4 . . . A-4 . . . . . . . . . . . = . . .", 1);
byte oBass = Pat("overBass", "A-2 . . . . . . . G-2 . . . . . . . F-2 . . . . . . . E-2 . . . A-1 . . =", 2);
byte oPad = Pat("overPad", "C-4 . . . . . . . B-3 . . . . . . . A-3 . . . . . . . G#3 . . . A-3 . . =", 6);
song.Subtunes.Add(new Subtune { Orderlists = {
    [0] = [oLead, silent, LOOP, 1], [1] = [oBass, silent, LOOP, 1], [2] = [oPad, silent, LOOP, 1],
} });

// Ticho
song.Subtunes.Add(new Subtune { Orderlists = { [0] = [silent, LOOP, 0], [1] = [silent, LOOP, 0], [2] = [silent, LOOP, 0] } });

// --- výstupy ---
byte[] sng = SngWriter.Write(song);
SngReader.Read(sng);                                   // kontrola: .sng sa dá načítať späť
var packed = Gt2Packer.PackPlayback(song, baseAddress: MUSIC_BASE);
byte[] image = packed.Prg[2..];
int end = MUSIC_BASE + image.Length;
if (end > 0xC000) throw new Exception($"hudba presahuje $C000 (koniec ${end:X4})");
Verify(image);
Directory.CreateDirectory(build);
File.WriteAllBytes(Path.Combine(assets, "music.sng"), sng);
File.WriteAllBytes(Path.Combine(assets, "music.bin"), image);
File.WriteAllBytes(Path.Combine(build, "music.sid"), packed.Sid);
Console.WriteLine($"music.sng {sng.Length} B, music.bin {image.Length} B (${MUSIC_BASE:X4}-${end - 1:X4}), " +
                  $"{song.Subtunes.Count} subtunes, {song.Patterns.Count} patternov, {song.Instruments.Count} nástrojov");
return 0;

// Kontrola v emulátore 6502: init + 500× play pre každý subtune – play musí skončiť (RTS) v rozumnom počte krokov
// a zapisovať len do vlastnej pamäte ($B000–$BFFF), SID ($D400–$D418) a ZP $02–$03 (tie má C#64 voľné).
static void Verify(byte[] image)
{
    for (int sub = 0; sub < 4; sub++)
    {
        var emu = new C64U_Code.Shared.Emulation.Emu6502();
        Array.Copy(image, 0, emu.Mem, MUSIC_BASE, image.Length);
        for (int i = 0x0002; i < 0x10000; i++)            // aj nulová stránka (review k9 č. 10); zásobník necháme
            if ((i < 0x0100 || i >= 0x0200) && (i < MUSIC_BASE || i >= 0xC000)) emu.Mem[i] = 0x55;
        byte[] before = (byte[])emu.Mem.Clone();
        emu.CallSub(MUSIC_BASE, (byte)sub, 10_000);
        long maxSteps = 0;
        var notes = new HashSet<(int, byte)>();             // (hlas, horný bajt frekvencie) pri zapnutom GATE
        for (int f = 0; f < 500; f++)
        {
            long s0 = emu.Cycles;
            emu.CallSub(MUSIC_BASE + 3, 0, 20_000);
            maxSteps = Math.Max(maxSteps, emu.Cycles - s0);
            for (int ch = 0; ch < 3; ch++)
                if ((emu.Mem[0xD404 + ch * 7] & 1) != 0) notes.Add((ch, emu.Mem[0xD401 + ch * 7]));

        }
        for (int a = 0x0002; a < 0x10000; a++)
        {
            bool allowed = (a >= MUSIC_BASE && a < 0xC000) || (a >= 0xD400 && a <= 0xD418) || (a >= 0x0100 && a < 0x0200)
                           || a == 0x02 || a == 0x03;      // ZP prehrávača (zpbase = $02)
            if (!allowed && emu.Mem[a] != before[a]) throw new Exception($"subtune {sub}: zápis na ${a:X4}");
        }
        Console.WriteLine($"subtune {sub}: OK, play najviac {maxSteps} cyklov, rôznych tónov s GATE: {notes.Count}");
        if (sub < 3 && notes.Count < 3) throw new Exception($"subtune {sub}: skladba nehrá (len {notes.Count} tónov)");
    }
}
