#!/usr/bin/env python3
"""
make_audio.py — turns the markdown recording script into the 4 section MP3s.

  pip install edge-tts          (and install ffmpeg: https://ffmpeg.org/download.html)
  python tools/make_audio.py odilxanivich-1-listening-audio-script.md

Output (default): ielts/odilxanivich-1-listening-section-1.mp3 ... section-4.mp3

Options
  --out DIR          output folder (default: ielts)
  --test-id ID       file prefix (default: odilxanivich-1-listening)
  --sections 1,3     only build some sections
  --rate -5%         speaking speed (default -3%; slower = more negative)
  --dry-run          print what would be spoken, with estimated length, and stop
  --fake             offline test mode: beeps instead of speech (checks timing/assembly only)

Each synthesized sentence is cached in .audio-cache/, so if your connection drops just run it again.
"""
import argparse, asyncio, hashlib, re, shutil, subprocess, sys, tempfile
from pathlib import Path

# Voice per speaker. List all voices with:  edge-tts --list-voices
VOICES = {
    "Narrator": "en-GB-SoniaNeural",
    "Han": "en-GB-LibbyNeural",
    "Maria": "en-IE-EmilyNeural",
    "Mr Park": "en-GB-RyanNeural",
    "Dr Morris": "en-GB-ThomasNeural",
    "Daniel": "en-AU-WilliamNeural",
    "Seo-yeon": "en-AU-NatashaNeural",
    "Professor Kang": "en-IE-ConnorNeural",
}
GENDER = {"Narrator": "Female", "Han": "Female", "Maria": "Female", "Mr Park": "Male",
          "Dr Morris": "Male", "Daniel": "Male", "Seo-yeon": "Female", "Professor Kang": "Male"}
LOCALE_ORDER = ["en-GB", "en-AU", "en-IE", "en-US", "en-CA", "en-NZ", "en-ZA", "en-IN"]
MIN_BYTES = 1500     # anything smaller is not real speech
TURN_GAP = 0.5       # seconds of silence between speakers
PARA_GAP = 0.6       # between paragraphs of the same speaker
DEFAULT_PAUSE = 3.0  # for a bare [pause]

LABEL = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")
PAUSE = re.compile(r"\*?\[pause(?:\s+(\d+)\s*seconds?)?\]\*?", re.I)
SPELLED = re.compile(r"\b(?:[A-Z]-){2,}[A-Z]\b")


def clean(t):
    t = SPELLED.sub(lambda m: ", ".join(m.group(0).split("-")), t)  # L-I-N-D -> "L, I, N, D,"
    return re.sub(r"[*_]", "", t).strip()


def parse(md):
    """-> {section_number: [("say", speaker, text) | ("gap", seconds)]}"""
    out, cur, speaker, fresh = {}, None, None, False
    for raw in md.splitlines():
        line = raw.strip()
        m = re.match(r"^##\s+SECTION\s+(\d)", line, re.I)
        if m:
            cur = out.setdefault(int(m.group(1)), []); speaker = None; continue
        if cur is None or not line or line.startswith(("#", "---", ">")):
            continue
        lab = LABEL.match(line)
        if lab:
            speaker, text = lab.group(1).strip(), lab.group(2)
            cur.append(("gap", TURN_GAP)) if cur else None
        elif speaker:
            text = line
            cur.append(("gap", PARA_GAP))
        else:
            continue
        if speaker not in VOICES:
            sys.exit(f"No voice set for speaker '{speaker}'. Add it to VOICES at the top of this file.")
        pieces = PAUSE.split(text)   # [text, secs|None, text, secs|None, text ...]
        for i, p in enumerate(pieces):
            if i % 2 == 0:
                if clean(p):
                    cur.append(("say", speaker, clean(p)))
            else:
                cur.append(("gap", float(p) if p else DEFAULT_PAUSE))
    return out


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"Command failed: {' '.join(cmd)}\n{r.stderr[-600:]}")


def est_seconds(text):  # ~2.4 words/second
    return max(0.4, len(text.split()) / 2.4)


async def synth_to(text, voice, rate, dest):
    """Write to a .part file and only rename it when it is real audio (no empty/partial files in the cache)."""
    import edge_tts
    part = Path(str(dest) + ".part")
    try:
        await edge_tts.Communicate(text, voice, rate=rate).save(str(part))
        if part.stat().st_size < MIN_BYTES:
            raise RuntimeError("audio too short")
        part.replace(dest)
    finally:
        part.unlink(missing_ok=True)


async def speak(text, voice, rate, dest, fake):
    if fake:
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=f=440:d={est_seconds(text):.2f}", "-ac", "1", "-ar", "24000", str(dest)])
        return
    for attempt in range(4):
        try:
            await synth_to(text, voice, rate, dest)
            return
        except Exception as e:  # network hiccup or rejected voice
            if attempt == 3:
                sys.exit(f"Speech service failed for voice {voice}: {e}\nChange that voice in VOICES (list them with: edge-tts --list-voices)")
            await asyncio.sleep(2 * (attempt + 1))


async def resolve_voices(rate):
    """Test every configured voice with a short sentence; swap any dead voice for a working one of the same gender."""
    import edge_tts
    tmp = Path(tempfile.mkdtemp(prefix="probe-"))
    avail = [v for v in await edge_tts.list_voices() if v["Locale"].startswith("en-")]
    avail.sort(key=lambda v: (LOCALE_ORDER.index(v["Locale"]) if v["Locale"] in LOCALE_ORDER else 99, v["ShortName"]))
    status = {}

    async def works(name):
        if name not in status:
            try:
                await synth_to("This is a test.", name, rate, tmp / f"{name}.mp3")
                status[name] = True
            except Exception:
                status[name] = False
        return status[name]

    chosen = {}
    for who, voice in list(VOICES.items()):
        if await works(voice) and voice not in chosen.values():
            chosen[who] = voice
            continue
        for v in avail:
            name = v["ShortName"]
            if v["Gender"] == GENDER.get(who, v["Gender"]) and name not in chosen.values() and name not in VOICES.values() and await works(name):
                chosen[who] = name
                print(f"  voice for {who}: {voice} is unavailable, using {name}")
                break
        else:
            sys.exit(f"No working voice found for {who}. Check your internet connection and run again.")
    VOICES.update(chosen)
    shutil.rmtree(tmp, ignore_errors=True)
    print("Voices:", ", ".join(f"{k}={v}" for k, v in VOICES.items()))


def to_wav(src, dst):
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(dst)], capture_output=True, text=True)
    return r.returncode == 0


def silence(sec, dst):
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{sec:.2f}", "-c:a", "pcm_s16le", str(dst)])


async def build(n, items, args, out_path):
    cache = Path(".audio-cache"); cache.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f"sec{n}-"))
    parts = []
    for i, it in enumerate(items):
        wav = tmp / f"{i:04d}.wav"
        if it[0] == "gap":
            silence(it[1], wav)
        else:
            _, who, text = it
            key = hashlib.sha1(f"{VOICES[who]}|{args.rate}|{args.fake}|{text}".encode()).hexdigest()[:20]
            mp3 = cache / f"{key}.mp3"
            for attempt in range(2):
                if not mp3.exists() or mp3.stat().st_size < MIN_BYTES:
                    mp3.unlink(missing_ok=True)
                    await speak(text, VOICES[who], args.rate, mp3, args.fake)
                    print(f"  section {n}: {i + 1}/{len(items)} {who}: {text[:50]}")
                if to_wav(mp3, wav):
                    break
                mp3.unlink(missing_ok=True)   # corrupt cache entry: delete and synthesize again
            else:
                sys.exit(f"Could not create audio for: {text[:60]}")
        parts.append(wav)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts))
    joined = tmp / "joined.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined), "-ac", "1", "-ar", "44100", "-b:a", "64k", str(out_path)])
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script")
    ap.add_argument("--out", default="ielts")
    ap.add_argument("--test-id", default="odilxanivich-1-listening")
    ap.add_argument("--sections", default="")
    ap.add_argument("--rate", default="-3%")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fake", action="store_true")
    args = ap.parse_args()

    for tool in ("ffmpeg",):
        if subprocess.run(["which" if sys.platform != "win32" else "where", tool], capture_output=True).returncode:
            sys.exit("ffmpeg is not installed: https://ffmpeg.org/download.html")
    if not args.fake and not args.dry_run:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            sys.exit("Run first:  pip install edge-tts")

    if not args.fake and not args.dry_run:
        asyncio.run(resolve_voices(args.rate))
    secs = parse(Path(args.script).read_text(encoding="utf-8"))
    want = {int(x) for x in args.sections.split(",") if x} or set(secs)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    for n in sorted(secs):
        if n not in want:
            continue
        items = secs[n]
        total = sum(est_seconds(i[2]) if i[0] == "say" else i[1] for i in items)
        print(f"Section {n}: {sum(i[0] == 'say' for i in items)} lines, ~{total / 60:.1f} min")
        if args.dry_run:
            for it in items:
                print("   ", f"[{it[1]}] {it[2][:70]}" if it[0] == "say" else f"(pause {it[1]:g}s)")
            continue
        out = Path(args.out) / f"{args.test_id}-section-{n}.mp3"
        asyncio.run(build(n, items, args, out))
        print(f"Created {out}")


if __name__ == "__main__":
    main()