"""Whisper word-level transcription for an episode's recordings.

Usage: python transcribe.py <episode_dir> <file> [<file> ...]
       python transcribe.py <episode_dir> --stretch <file> <from> <to>   listen again to one stretch (gs_cut.py runs it)
Writes <episode_dir>/work/<stem>.whisper.json  (prompted with the section's script: spelling of terms, cue text)
       <episode_dir>/work/noprompt/<stem>.json (no prompt: keeps repeated phrases, so retakes are visible)
then the recording-diff report (recording_diff.py -> work/recording-diff.md).
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

import gs_env


def decode(path):
    # faster-whisper's own decoder breaks with av>=19, so decode with ffmpeg to 16 kHz mono float
    pcm = subprocess.run([gs_env.FFMPEG, "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0


def script_prompt(ep, stem=None):
    s = (ep / "script.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```\n(.*?)```", s, re.S)
    prefix = gs_env.LANG.get("whisper_prompt_prefix", "以下是普通话的句子。" if gs_env.LANG.get("narration", "zh") == "zh" else "")
    squeeze = (lambda s: re.sub(r"\s+", "", s)) if gs_env.CJK else (lambda s: re.sub(r"\s+", " ", s).strip())
    m = re.match(r"(?:cam|voice)-([SXC]\d+[a-z]?|END)$", stem or "")
    if m:                    # per-shot recording: only that section's text; beat sheets (●) get no prompt
        for b in blocks:
            sec = re.search(rf"^{m.group(1)}\s+(.*?)(?=^\S|\Z)", b, re.S | re.M)
            if sec:
                body = sec.group(1)
                if "●" in body:
                    return None
                body = re.sub(r"【[^】]*】|\[[A-Z][^\]]*\]", "", body)
                return prefix + squeeze(body)[:220]
    text = re.sub(r"S\d+\s+", "", blocks[0]) if blocks else ""
    return prefix + squeeze(text)[:200]


_model = None


def run(audio, prompt):
    """One Whisper pass -> ({file, duration, segments[words]}, readable lines)."""
    global _model
    if _model is None:
        _model = WhisperModel(str(gs_env.WHISPER_MODEL), device=gs_env.cfg("whisper", "device", "cpu"),
                              compute_type=gs_env.cfg("whisper", "compute_type", "int8"))
    segs, info = _model.transcribe(audio, language=gs_env.LANG.get("narration", "zh"), word_timestamps=True, initial_prompt=prompt,
                                   vad_filter=True, vad_parameters={"min_silence_duration_ms": 300},
                                   condition_on_previous_text=False)
    out = {"duration": info.duration, "segments": []}
    lines = []
    for s in segs:
        out["segments"].append({"start": s.start, "end": s.end, "text": s.text.strip(),
                                "words": [{"start": w.start, "end": w.end, "word": w.word, "p": w.probability}
                                          for w in s.words]})
        lines.append(f"[{s.start:7.2f} -> {s.end:7.2f}] {s.text.strip()}")
    return out, lines


def stretch(ep, f, a, b, pad=0.4):
    """Listen again to seconds a-b of one recording alone and merge the words into its no-prompt transcript
    (the old file is kept beside it). For a stretch where Whisper heard sound but wrote no words: it gives one word
    that lasts for seconds, and a retake hidden inside it is never found. Returns the text."""
    ep = Path(ep)
    path = ep / "raw" / f
    stem = path.name.split(".")[0]
    js = ep / "work" / "noprompt" / f"{stem}.json"
    d = json.loads(js.read_text(encoding="utf-8"))
    audio = decode(path)
    a0, b0 = max(0.0, a - pad), min(len(audio) / 16000, b + pad)
    out, _ = run(audio[int(a0 * 16000):int(b0 * 16000)], None)
    words = [dict(w, start=round(w["start"] + a0, 2), end=round(w["end"] + a0, 2)) for s in out["segments"] for w in s["words"]]
    words = [w for w in words if a - 0.05 <= (w["start"] + w["end"]) / 2 <= b + 0.05]
    if not words:
        return ""
    bak = js.with_name(f"{stem}.before-stretch-{time.strftime('%Y%m%d-%H%M%S')}.json")
    bak.write_text(js.read_text(encoding="utf-8"), encoding="utf-8")
    for s in d["segments"]:                       # the old words of that stretch go; a long one is cut short at a
        keep = []
        for w in s.get("words", []):
            if w["start"] < a < w["end"]:
                w["end"] = round(a, 2)
            if not (a <= (w["start"] + w["end"]) / 2 <= b):
                keep.append(w)
        s["words"] = keep
    text = "".join(w["word"] for w in words).strip()
    d["segments"].append({"start": words[0]["start"], "end": words[-1]["end"], "text": text, "words": words,
                          "stretch": [round(a, 2), round(b, 2)]})
    d["segments"].sort(key=lambda s: s["words"][0]["start"] if s.get("words") else s["start"])
    js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return text


def main():
    if "--stretch" in sys.argv:                   # transcribe.py <episode_dir> --stretch <file> <from> <to>
        i = sys.argv.index("--stretch")
        print("STRETCH " + stretch(sys.argv[1], sys.argv[i + 1], float(sys.argv[i + 2]), float(sys.argv[i + 3])))
        return
    ep = Path(sys.argv[1])
    work = ep / "work"
    (work / "noprompt").mkdir(parents=True, exist_ok=True)
    for f in (a for a in sys.argv[2:] if not a.startswith("--")):
        path = ep / "raw" / f
        stem = path.name.split(".")[0]
        t = time.time()
        audio = decode(path)
        out, lines = run(audio, script_prompt(ep, stem))
        out["file"] = f
        (work / f"{stem}.whisper.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        (work / f"{stem}.whisper.txt").write_text("\n".join(lines), encoding="utf-8")
        np_js = work / "noprompt" / f"{stem}.json"
        if np_js.exists() and np_js.stat().st_mtime >= path.stat().st_mtime - 1 and "--redo" not in sys.argv:
            print(f"   (no-prompt pass: reusing the one intake.py made, {np_js.name})")
        else:
            raw, _ = run(audio, None)
            raw["file"] = f
            np_js.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"== {f}  ({out['duration']:.1f}s audio, two passes {time.time() - t:.0f}s)")
        print("\n".join(lines))
    import recording_diff
    recording_diff.report(ep.name)


if __name__ == "__main__":
    main()
