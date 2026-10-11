"""Whisper word-level transcription for an episode's recordings.

Usage: python transcribe.py <episode_dir> <file> [<file> ...]
Writes <episode_dir>/work/<stem>.whisper.json  (segments + words, seconds) and a readable .txt
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


def script_prompt(ep):
    s = (ep / "script.md").read_text(encoding="utf-8")
    block = re.search(r"```\n(.*?)```", s, re.S)
    text = re.sub(r"(?m)^((?:S|C)\d+[a-z]?|END)\s+", "", block.group(1)) if block else ""
    prefix = gs_env.LANG.get("whisper_prompt_prefix", "")
    joiner = "" if gs_env.LANG.get("length_unit", "cjk") == "cjk" else " "
    return prefix + joiner.join(text.split())[:200]


def main():
    ep = Path(sys.argv[1])
    work = ep / "work"
    work.mkdir(exist_ok=True)
    model = WhisperModel(str(gs_env.WHISPER_MODEL), device=gs_env.cfg("whisper", "device", "cpu"),
                         compute_type=gs_env.cfg("whisper", "compute_type", "int8"))
    prompt = script_prompt(ep)
    for f in sys.argv[2:]:
        path = ep / "raw" / f
        t = time.time()
        audio = decode(path)
        segs, info = model.transcribe(audio, language=gs_env.LANG.get("narration", "zh"), word_timestamps=True, initial_prompt=prompt,
                                      vad_filter=True, vad_parameters={"min_silence_duration_ms": 300},
                                      condition_on_previous_text=False)
        out = {"file": f, "duration": info.duration, "segments": []}
        lines = []
        for s in segs:
            out["segments"].append({"start": s.start, "end": s.end, "text": s.text.strip(),
                                    "words": [{"start": w.start, "end": w.end, "word": w.word, "p": w.probability}
                                              for w in s.words]})
            lines.append(f"[{s.start:7.2f} -> {s.end:7.2f}] {s.text.strip()}")
        stem = path.name.split(".")[0]
        (work / f"{stem}.whisper.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        (work / f"{stem}.whisper.txt").write_text("\n".join(lines), encoding="utf-8")
        print(f"== {f}  ({info.duration:.1f}s audio, {time.time() - t:.0f}s)")
        print("\n".join(lines))


if __name__ == "__main__":
    main()
