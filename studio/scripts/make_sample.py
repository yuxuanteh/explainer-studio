"""Try-it sample: a four-line short you can run through the whole pipeline before recording anything.

    python make_sample.py [--record]

Creates the standalone short ss900-sample (script, folders) and its "recording": the computer's own speech voice reads
the script the way a real session goes (a spoken slate, a slip, a pause, the line read again), so the automatic cut
has a retake to find. Then:
    python gs_run.py ss900-sample voicecut          cut it and build the voice cut
    python gs_review.py                             http://localhost:8770: watch it, leave notes, try the editing page
    python gs_run.py ss900-sample preview           480p with animation stubs (needs the animation part)
With --record (or when the computer has no voice for your narration language) nothing is synthesised: read the four
lines yourself into your phone or camera, put the file in the sample's raw/ folder and run `intake.py ss900-sample`.
Delete the sample afterwards: <project>/shorts/ss900-sample, <studio>/shorts/ss900-sample, <studio>/web/ep/ss900-sample.
"""
import os
import shutil
import subprocess
import sys

import gs_env

EP = "ss900-sample"
TEXT = {
    "en": dict(title="Why does a mountain stop growing?", field="Geology",
               slate="zero zero, X zero one.",
               lines=["Why does a mountain stop growing?",
                      "Deep below, the crust is still pushing it up, a few millimetres every year.",
                      "But on top, rain and ice are wearing it down just as fast.",
                      "So the height of a mountain is a tug of war, and the peak you see is where the two sides are even."],
               slip="Deep below, the crust is still pulling it"),
    "zh": dict(title="山为什么不会一直长高?", field="地质学",
               slate="零零, X 零一。",
               lines=["山为什么不会一直长高?",
                      "在很深的地下, 地壳还在把它往上推, 每年几毫米。",
                      "可是在山顶, 雨水和冰也在用差不多的速度把它磨掉。",
                      "所以一座山的高度, 是两股力量拉出来的, 你看到的山顶, 就是两边打平的地方。"],
               slip="在很深的地下, 地壳还在把它往下"),
}


def speech(lang, T):
    """The session as SSML-ish pieces: (text, pause after in ms)."""
    L = T["lines"]
    return [(T["slate"], 3000), (L[0], 700), (T["slip"], 2000), (L[1], 700), (L[2], 700), (L[3], 1500)]


def synth(lang, T, wav):
    parts = speech(lang, T)
    if os.name == "nt":
        ssml = "".join(f"{t}<break time='{p}ms'/>" for t, p in parts).replace('"', "")
        culture = {"zh": "zh-CN", "en": "en-US"}.get(lang, lang)
        ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$v = $s.GetInstalledVoices() | Where-Object {{ $_.VoiceInfo.Culture.Name -like '{lang}*' }} | Select-Object -First 1; "
              "if (-not $v) { exit 3 }; $s.SelectVoice($v.VoiceInfo.Name); $s.Rate = 0; "
              f"$s.SetOutputToWaveFile('{wav}'); "
              f"$s.SpeakSsml(\"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{culture}'>{ssml}</speak>\"); $s.Dispose()")
        return subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True).returncode == 0
    if sys.platform == "darwin":
        voice = {"zh": "Tingting", "en": "Samantha"}.get(lang)
        if not voice:
            return False
        text = " ".join(f"{t} [[slnc {p}]]" for t, p in parts)
        aiff = wav.with_suffix(".aiff")
        ok = subprocess.run(["say", "-v", voice, "-o", str(aiff), text], capture_output=True).returncode == 0
        if ok:
            subprocess.run([gs_env.FFMPEG, "-v", "error", "-y", "-i", str(aiff), str(wav)], check=True)
            aiff.unlink()
        return ok
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        return False
    text = " ".join(f"{t} <break time='{p}ms'/>" for t, p in parts)
    return subprocess.run([exe, "-m", "-v", {"zh": "cmn", "en": "en"}.get(lang, lang), "-s", "150", "-w", str(wav), text],
                          capture_output=True).returncode == 0


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    lang = gs_env.LANG.get("narration", "en")
    T = TEXT.get(lang)
    g, c = gs_env.ep_dir(EP), gs_env.code_dir(EP)
    if not g.exists():
        if not T:
            T = TEXT["en"]
            print(f"no sample script in '{lang}': the English one is written; translate script.md's four lines, then record them")
        r = subprocess.run([sys.executable, "new_short.py", "900", "sample", T["title"], T["field"]], cwd=gs_env.STUDIO / "scripts",
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode:
            raise SystemExit(r.stdout + r.stderr)
        s = (g / "script.md").read_text(encoding="utf-8")
        a, b = s.index("```\n") + 4, s.index("```", s.index("```\n") + 4)
        block = "".join(f"X{k + 1:02d}  {line}\n" for k, line in enumerate(T["lines"]))
        (g / "script.md").write_text(s[:a] + block + s[b:], encoding="utf-8")
        edl = (c / "edl.py").read_text(encoding="utf-8")
        t1, t2 = (T["title"], "") if len(T["title"]) < 16 else (T["title"].rsplit(" ", 2)[0], " ".join(T["title"].rsplit(" ", 2)[1:]))
        (c / "edl.py").write_text(edl.replace('("Title line one", "Title line two?")', repr((t1, t2))), encoding="utf-8")
        print(f"sample short created: {g}")
    T = TEXT.get(lang) or TEXT["en"]
    wav = g / "raw" / "voice-X01.wav"
    if "--record" in sys.argv or lang not in TEXT:
        made = False
    else:
        made = wav.exists() or synth(lang, T, wav)
    if made:
        print(f"synthetic recording: {wav}\nnext:  python gs_run.py {EP} voicecut   (then python gs_review.py and open http://localhost:8770)")
    else:
        print(f"no synthetic voice for '{lang}' on this computer (or --record). Record it yourself, about 30 seconds:\n"
              f"  say \"{T['slate']}\", wait 3 seconds, then read the four lines in {g / 'script.md'}\n"
              f"  (make one slip on purpose: stop, wait 2 seconds, read that whole line again)\n"
              f"  put the file in {g / 'raw'} and run:  python intake.py {EP}   then   python intake.py {EP} --apply")


if __name__ == "__main__":
    main()
