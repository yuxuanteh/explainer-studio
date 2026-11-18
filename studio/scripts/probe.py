"""What this computer is, how fast it is, and about how long each step of the pipeline will take on it.

    python probe.py [--minutes 6] [--short 1] [--model large-v3|medium|small] [--json]

Runs BEFORE anything is installed (Python's standard library only), so the person can decide what to install knowing
what it will cost them in time and disk space. It reads the processor, memory, graphics card and free disk space, runs
two short speed tests (one processor core; and, when ffmpeg is already there, a real video encode on all cores), and
scales timings that were measured on a reference computer.

The reference computer: Intel Core Ultra 7 155H laptop (16 cores / 22 threads), 16 GB memory, no separate graphics
card, Windows 11. Its timings are in REF below. The estimates are rough (expect half to double): the number of
animated shots, how busy they are, and how many retakes a recording holds all move them.
"""
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

STUDIO = Path(__file__).resolve().parent.parent
WIN, MAC = os.name == "nt", sys.platform == "darwin"

# Measured on the reference computer (2026-11). Seconds of computing per second of material, unless noted.
REF = {
    "single": 1.0,               # filled below: SHA-256 MB/s of one core on the reference computer
    "encode_fps": 1.0,           # filled below: libx264 medium, 1080p test pattern, frames per second
    "eff_threads": 9.5,          # 22 threads counted as min(threads, 16) ** 0.8
    "whisper": {"large-v3": 0.70, "medium": 0.35, "small": 0.13},   # per second of RECORDING, CPU int8 (large-v3 measured;
    "whisper_load": 25,          # medium / small scaled from their size); + seconds to load the model, once per run
    "record_ratio": 1.6,         # a recording is about this much longer than what is kept (slates, retakes, pauses)
    "cut": 0.02,                 # automatic cut, per second of recording
    "voicecut": 0.30,            # voice cut build (480p, cards + camera), per second of video
    "render_480": 0.35,          # animation frames at 480p, per second of animated video
    "render_1080": 0.85,         # animation frames at 1080p
    "per_shot": 9,               # per shot and run: start the browser, render, check the shot is deterministic
    "shots_per_min": 4,          # a typical video has about this many shots per minute
    "build_480": 0.20,           # assemble + mix + burn subtitles at 480p, per second of video
    "build_1080": 0.45,          # the same at 1080p
    "checks": 60,                # script check, cuts in silence, QA report: seconds per run, flat
    "anim_share": 0.7,           # share of a video that is animation (the rest is camera)
}
REF["single"], REF["encode_fps"] = 2000.0, 115.0   # measured with the computer otherwise idle


def sh(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def ps(script):
    return sh(["powershell", "-NoProfile", "-Command", script], timeout=40)


def hardware():
    h = {"os": f"{platform.system()} {platform.release()}", "arch": platform.machine(), "threads": os.cpu_count() or 1,
         "cpu": platform.processor() or "", "cores": None, "ram_gb": None, "gpu": [], "nvidia_gb": None}
    if WIN:
        out = ps("$c = Get-CimInstance Win32_Processor | Select-Object -First 1; $c.Name; $c.NumberOfCores; "
                 "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1); "
                 "(Get-CimInstance Win32_VideoController).Name").splitlines()
        if len(out) >= 3:
            h["cpu"], h["cores"], h["ram_gb"], h["gpu"] = out[0].strip(), int(out[1] or 0) or None, float(out[2].replace(",", ".") or 0) or None, [g.strip() for g in out[3:] if g.strip()]
    elif MAC:
        h["cpu"] = sh(["sysctl", "-n", "machdep.cpu.brand_string"]) or h["cpu"]
        h["cores"] = int(sh(["sysctl", "-n", "hw.physicalcpu"]) or 0) or None
        h["ram_gb"] = round(int(sh(["sysctl", "-n", "hw.memsize"]) or 0) / 2 ** 30, 1) or None
        h["gpu"] = [l.split(":", 1)[1].strip() for l in sh(["system_profiler", "SPDisplaysDataType"], 40).splitlines() if "Chipset Model" in l]
    else:
        info = Path("/proc/cpuinfo").read_text(errors="replace") if Path("/proc/cpuinfo").exists() else ""
        h["cpu"] = next((l.split(":", 1)[1].strip() for l in info.splitlines() if l.startswith("model name")), h["cpu"])
        mem = Path("/proc/meminfo").read_text(errors="replace") if Path("/proc/meminfo").exists() else ""
        kb = next((int(l.split()[1]) for l in mem.splitlines() if l.startswith("MemTotal")), 0)
        h["ram_gb"] = round(kb / 2 ** 20, 1) or None
        h["gpu"] = [l.split(":", 2)[-1].strip() for l in sh(["lspci"]).splitlines() if "VGA" in l or "3D controller" in l]
    nv = sh(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
    if nv:
        name, memmb = [x.strip() for x in nv.splitlines()[0].split(",")][:2]
        h["nvidia_gb"] = round(float(memmb) / 1024, 1)
        if name not in h["gpu"]:
            h["gpu"].append(name)
    for label, p in (("studio", STUDIO), ("home", Path.home())):
        try:
            h[f"free_gb_{label}"] = round(shutil.disk_usage(p).free / 1e9, 1)
        except OSError:
            h[f"free_gb_{label}"] = None
    return h


def bench_single(seconds=0.7, rounds=3):
    """SHA-256 over memory on one core, MB per second: a stand-in for single-core speed. Best of three short rounds,
    so a busy moment does not drag the number down."""
    block = bytes(4 << 20)
    best = 0.0
    for _ in range(rounds):
        hsh, n, t0 = hashlib.sha256(), 0, time.perf_counter()
        while time.perf_counter() - t0 < seconds:
            hsh.update(block)
            n += 4
        best = max(best, n / (time.perf_counter() - t0))
    return best


def find_ffmpeg():
    f = shutil.which("ffmpeg")
    if f:
        return f
    try:
        import tomllib
        b = tomllib.loads((STUDIO / "studio.toml").read_text(encoding="utf-8")).get("paths", {}).get("ffmpeg_bin", "")
        f = Path(b) / ("ffmpeg.exe" if WIN else "ffmpeg")
        return str(f) if b and f.exists() else None
    except (OSError, ValueError):
        return None


def bench_encode(ffmpeg):
    """Encode 6 s of a moving 1080p test pattern with libx264 on all cores: frames per second."""
    out = Path(tempfile.gettempdir()) / "explainer-studio-probe.mp4"
    t0 = time.perf_counter()
    r = subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=30:d=6", "-c:v", "libx264",
                        "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", str(out)], capture_output=True, timeout=600)
    dt = time.perf_counter() - t0
    out.unlink(missing_ok=True)
    return 180 / dt if r.returncode == 0 else None


def hw_encoders(ffmpeg):
    """Hardware H.264 encoders that really work here (each is tried on one second of video)."""
    ok = []
    for name, args in (("h264_nvenc", ["-cq", "20", "-preset", "p6"]), ("h264_qsv", ["-global_quality", "20", "-preset", "slow"]),
                       ("h264_videotoolbox", ["-q:v", "65"]), ("h264_amf", ["-quality", "quality"])):
        try:
            r = subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=1", "-c:v", name, *args,
                                "-f", "null", "-"], capture_output=True, timeout=60)
            if r.returncode == 0:
                ok.append((name, ["-c:v", name, *args]))
        except (OSError, subprocess.SubprocessError):
            pass
    return ok


def fmt(sec):
    if sec < 90:
        return f"{max(sec, 1):.0f} s"
    if sec < 5400:
        return f"{sec / 60:.0f} min"
    return f"{sec / 3600:.1f} h"


def estimate(h, single, enc_fps, minutes, short, model):
    eff = min(h["threads"], 16) ** 0.8
    cpu = (REF["single"] / single) * (REF["eff_threads"] / eff)          # > 1 = slower than the reference
    video = (REF["encode_fps"] / enc_fps) if enc_fps else cpu
    one = REF["single"] / single                                         # the browser draws frames on one core
    gpu = bool(h["nvidia_gb"] and h["nvidia_gb"] >= (5 if model == "large-v3" else 3))
    w = REF["whisper"][model] * (0.08 if gpu else cpu)
    L, S = minutes * 60, short * 60
    rec = (L + S) * REF["record_ratio"]
    anim = (L + S) * REF["anim_share"]
    shots = (minutes + short) * REF["shots_per_min"] * REF["per_shot"] * one
    rows = [
        ("Sort the recording session and write down every word (Whisper)", rec * w + REF["whisper_load"] * cpu,
         "graphics card" if gpu else "processor", "whisper"),
        ("Automatic first cut + voice cut for the review page", rec * REF["cut"] * cpu + (L + S) * REF["voicecut"] * video + REF["checks"] * cpu, "", "core"),
        ("Animation at 480p: draw the frames, assemble, mix, check", shots + anim * REF["render_480"] * one + (L + S) * REF["build_480"] * video + REF["checks"] * cpu,
         "each round of notes redraws only the shots you commented on", "animation"),
        ("Final 1080p master + the 9:16 short + subtitle files", shots + anim * REF["render_1080"] * one + (L + S) * REF["build_1080"] * video + REF["checks"] * cpu, "", "core"),
    ]
    return rows, {"cpu_factor": round(cpu, 2), "video_factor": round(video, 2), "whisper_on_gpu": gpu}


def advice(h, enc_fps, model, hw):
    out = []
    ram = h["ram_gb"] or 0
    if ram and ram < 8:
        out.append(f"Memory is {ram} GB. The large-v3 speech model wants about 4 GB free and a 1080p animation render about 2 GB: "
                   "choose the `small` or `medium` model and close other programs while rendering.")
    elif ram and ram < 12 and model == "large-v3":
        out.append(f"Memory is {ram} GB: large-v3 will run, but close the browser and other heavy programs while it does.")
    if h["nvidia_gb"]:
        out.append(f"NVIDIA graphics card with {h['nvidia_gb']} GB: speech recognition can run on it, about ten times faster "
                   "(set [whisper] device = \"cuda\", compute_type = \"float16\"; needs NVIDIA's cuBLAS and cuDNN libraries).")
    if hw:
        out.append(f"A hardware video encoder works here ({hw[0][0]}): the 1080p master encodes faster with "
                   f"[video] final_encoder = {json.dumps(hw[0][1])}")
    free = h.get("free_gb_studio")
    if free is not None and free < 12:
        out.append(f"Only {free} GB free on the studio's disk. A full install is about 5 GB and every episode's render cache "
                   "1-3 GB more: free some space or put the studio folder on another disk.")
    if enc_fps is None:
        out.append("ffmpeg is not installed yet, so the video-encode test was skipped and those estimates lean on the "
                   "processor test alone. Run this again after `setup_studio.py install core` for better numbers.")
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    opt = {a[i]: a[i + 1] for i in range(len(a) - 1) if a[i].startswith("--")}
    minutes, short, model = float(opt.get("--minutes", 6)), float(opt.get("--short", 1)), opt.get("--model", "large-v3")
    h = hardware()
    single = bench_single()
    ff = find_ffmpeg()
    enc = bench_encode(ff) if ff else None
    hw = hw_encoders(ff) if ff else []
    rows, factors = estimate(h, single, enc, minutes, short, model)
    tips = advice(h, enc, model, hw)
    if "--json" in a:
        print(json.dumps({"hardware": h, "single_mb_s": round(single), "encode_fps": enc and round(enc, 1), "factors": factors,
                          "hardware_encoders": [n for n, _ in hw],
                          "estimate": [{"step": s, "seconds": round(t), "note": n, "part": p} for s, t, n, p in rows], "advice": tips},
                         ensure_ascii=False, indent=1))
        return
    print("THIS COMPUTER")
    print(f"  processor   {h['cpu']}  ({h['cores'] or '?'} cores, {h['threads']} threads)")
    print(f"  memory      {h['ram_gb'] or '?'} GB")
    print(f"  graphics    {', '.join(h['gpu']) or 'not detected'}" + (f"  (NVIDIA, {h['nvidia_gb']} GB)" if h["nvidia_gb"] else ""))
    print(f"  free disk   {h.get('free_gb_studio')} GB where the studio is")
    print(f"  system      {h['os']} {h['arch']}")
    print("\nSPEED TESTS (reference laptop = 100 %)")
    print(f"  one processor core   {single / REF['single']:.0%}")
    print(f"  video encode         " + (f"{enc / REF['encode_fps']:.0%}  ({enc:.0f} frames per second at 1080p)" if enc else "not tested (no ffmpeg yet)"))
    print(f"\nABOUT HOW LONG, for a {minutes:g}-minute video with a {short:g}-minute short (speech model: {model})")
    for step, t, note, _ in rows:
        print(f"  {fmt(t):>8s}   {step}" + (f"  [{note}]" if note else ""))
    print(f"  {fmt(sum(t for _, t, _, _ in rows)):>8s}   computer time in total, spread over the steps (your own review time is on top)")
    print("  Rough numbers: expect anything from half to double. Close other heavy programs before a build: a busy")
    print("  computer can take twice as long, and this test itself reads low when something else is running.")
    if tips:
        print("\nWORTH KNOWING")
        for t in tips:
            print("  - " + t)


if __name__ == "__main__":
    main()
