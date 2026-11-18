"""The one way to build a piece. Every check runs in order and the run stops at the first thing that is wrong, so a
mistake never costs a render and no check depends on being remembered.

    python gs_run.py <EPISODE> voicecut            automatic cut -> cuts in silence -> voice cut(s) for the review page
    python gs_run.py <EPISODE> preview [ids...]    480p: script check, cuts, shot modules, determinism, render (only
                                                   the named shots, or all), build long + short, motion QA, QA report
    python gs_run.py <EPISODE> final               1080p master + short + subtitle files
    options: --keep-cut   do not rerun gs_cut.py (it is rerun by default; the director's edit.json always survives)
             --no-anim    preview / final without the animation engine: plain cards where animation would go

One run at a time on this computer (render.lock); every step has a time limit, so a frozen ffmpeg or browser ends
the run instead of hanging it. Lines start with "=== " (a step), "WARN ", "FAILED " or "READY " so progress can be
followed; full output of each step is in <studio>/render/<EPISODE>/logs/.
"""
import atexit
import os
import subprocess
import sys
import time

import gs_env

PY = sys.executable
HERE = gs_env.STUDIO / "scripts"
if "--no-anim" in sys.argv:
    os.environ["GS_NO_ANIM"] = "1"
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}
LIMIT = {"cut": 7200, "check": 300, "voicecut": 1800, "script": 300, "stubs": 120, "determinism": 1800, "render": 5400,
         "build": 3600, "short": 3600, "qa": 1800, "srt": 300, "final-render": 14400}


def say(s):
    print(s, flush=True)


alive = gs_env.pid_alive


def lock():
    f = gs_env.RENDER / "run.lock"
    said = False
    while True:
        try:
            fd = os.open(f, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            atexit.register(lambda: f.unlink(missing_ok=True))
            return
        except FileExistsError:
            try:
                other = int(f.read_text().strip() or 0)
            except (OSError, ValueError):
                other = 0
            if not other or not alive(other):
                f.unlink(missing_ok=True)
                continue
            if not said:
                say(f"=== waiting: another run is going (pid {other})")
                said = True
            time.sleep(15)


class Run:
    def __init__(self, ep):
        self.ep = ep
        self.logs = gs_env.RENDER / ep / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.times = []

    def step(self, name, args, limit, must=True, fail_if=()):
        say(f"=== {name}")
        log = self.logs / f"{name.replace(' ', '-')}.log"
        t0 = time.time()
        try:
            r = subprocess.run([PY, *args], cwd=HERE, env=ENV, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=LIMIT[limit], stdin=subprocess.DEVNULL)
            out, code = r.stdout + r.stderr, r.returncode
        except subprocess.TimeoutExpired as e:
            out, code = (e.stdout or "") + f"\nSTALL: no end after {LIMIT[limit]} s", 124
            gs_env.kill_tree(("ffmpeg",))
        log.write_text(out if isinstance(out, str) else out.decode("utf-8", "replace"), encoding="utf-8")
        self.times.append((name, round(time.time() - t0, 1)))
        say(f"    {time.time() - t0:.0f} s")
        bad = code != 0 or any(k in out for k in fail_if)
        if bad:
            say(f"{'FAILED' if must else 'WARN'} {name}: see {log}\n" + "\n".join(out.strip().splitlines()[-8:]))
            if must:
                sys.exit(1)
        return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2 or args[1] not in ("voicecut", "preview", "final"):
        print(__doc__)
        return
    ep, mode, ids = args[0], args[1], args[2:]
    lock()
    import gs_episode as G
    R = Run(ep)
    t0 = time.time()
    code = gs_env.code_dir(ep)
    hand = bool(getattr(G.load(ep), "SHOTS", None) or getattr(G.load(ep), "SHORT_SHOTS", None)) and not (code / "edl_auto.py").exists()
    if mode == "voicecut" and "--keep-cut" not in sys.argv and not hand:
        out = R.step("automatic cut", ["gs_cut.py", ep], "cut")
        for line in out.splitlines():
            if line.startswith("- "):
                say("  " + line)
    E = G.load(ep)
    has_long, has_short = bool(E.SHOTS), bool(E.SHORT_SHOTS)
    if not (has_long or has_short):
        say("FAILED: no cut yet (run `gs_run.py <EP> voicecut` first)")
        sys.exit(1)
    if mode == "final":
        # a subtitle the director changed after step 6 has no translation any more (CUE_EN / CUE_JA are keyed on the
        # narration text); stop here instead of shipping an empty translated line
        missing = []
        for name, jname in (("CUES", "JA"), ("SHORT_CUES", "SHORT_JA")):
            rows, ja = getattr(E, name, None) or [], getattr(E, jname, None) or []
            for i, (*_, zh, en) in enumerate(rows):
                lack = [lang for lang, v in ((G.SUB_LANGS[1], en), (G.SUB_LANGS[2], ja[i] if i < len(ja) else "")) if lang and not str(v).strip()]
                if lack and zh.strip():
                    missing.append(f"  {name} · {'+'.join(lack)} · {zh.strip()}")
        if missing:
            say(f"FAILED translations: {len(missing)} subtitle(s) without a translation "
                "(add them to CUE_EN / CUE_JA in edl.py)\n" + "\n".join(missing[:40]))
            sys.exit(1)
        say("=== translations: every subtitle has its translation(s)")
    if has_long:
        R.step("cuts in silence", ["gs_episode.py", ep, "check"], "check", fail_if=("cut problem",))
    if has_short and has_long:
        R.step("cuts in silence (short)", ["gs_episode.py", ep, "check", "short"], "check", fail_if=("cut problem",))
    if has_short and not has_long:
        R.step("cuts in silence", ["gs_episode.py", ep, "check"], "check", fail_if=("cut problem",))
    ready = []
    if mode == "voicecut":
        if has_long:
            ready.append(R.step("voice cut", ["gs_voicecut.py", ep], "voicecut").strip().splitlines()[-1])
        if has_short:
            ready.append(R.step("voice cut (short)", ["gs_voicecut.py", ep, "short"], "voicecut").strip().splitlines()[-1])
    else:
        out = R.step("script check", ["check_script.py", ep], "script", must=False)
        if not G.NO_ANIM:
            R.step("shot modules", ["gs_web.py", ep, "stubs"], "stubs")
            R.step("determinism", ["gs_web.py", ep, "check", *ids], "determinism", fail_if=("NOT deterministic",))
        R.step(f"render {mode}", ["gs_episode.py", ep, "render", mode, *ids], "final-render" if mode == "final" else "render")
        if has_long:
            ready.append(R.step(f"build {mode}", ["gs_episode.py", ep, "build", mode], "build").strip().splitlines()[-1])
        if has_short:
            ready.append(R.step(f"short {mode}", ["gs_episode.py", ep, "short", mode], "short").strip().splitlines()[-1])
        if mode == "preview":
            if not G.NO_ANIM:
                if has_long:
                    out = R.step("motion QA", ["gs_web.py", ep, "qa"], "qa", must=False, fail_if=(" FAIL ",))
                if has_short:
                    out = R.step("motion QA (short)", ["gs_web.py", ep, "qa", "--short"], "qa", must=False, fail_if=(" FAIL ",))
            out = R.step("QA report", ["qa.py", ep, mode], "qa", must=False)
            say("  " + "\n  ".join(out.strip().splitlines()[-3:]))
        else:
            R.step("subtitle files", ["gs_episode.py", ep, "srt"], "srt")
    for line in ready:
        say(f"READY {line}")
    import json
    (R.logs / f"timings-{mode}.json").write_text(json.dumps({"mode": mode, "total_s": round(time.time() - t0, 1), "steps": R.times}, indent=1),
                                                encoding="utf-8")
    say(f"=== done in {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
