"""Listening samples for review: sample-30s (intro -> curious -> outro), moods-sampler, intro preview video."""
import subprocess

import numpy as np
import soundfile as sf

import gs_audio as A
import gs_env

M = gs_env.BRAND / "music"


def rd(name):
    return sf.read(str(M / name))[0].T


def to_m4a(wav):
    subprocess.run([gs_env.FFMPEG, "-v", "error", "-y", "-i", str(wav), "-c:a", "aac", "-b:a", "192k",
                    str(wav.with_suffix(".m4a"))], check=True)


def sample_30s():
    intro, cur, out = rd("intro-sting.wav"), rd("loop-curious.wav"), rd("outro-sting.wav")
    mix = np.zeros((2, int(30 * A.SR)))

    def put(x, at):
        i = int(at * A.SR)
        j = min(i + x.shape[1], mix.shape[1])
        mix[:, i:j] += x[:, :j - i]

    put(intro, 0.0)
    put(A.fade(np.concatenate([cur, cur], 1)[:, :int(20.6 * A.SR)], fin=0.5, fout=1.2) * 0.9, 4.0)
    put(out, 24.2)
    A.write(M / "sample-30s.wav", A.master(A.fade(mix, fout=0.8), lufs_like_db=-16))
    to_m4a(M / "sample-30s.wav")


def moods():
    parts = [A.fade(rd(f"loop-{m}.wav")[:, :int(8 * A.SR)], fin=0.2, fout=0.8)
             for m in ["curious", "tense", "calm", "epic"]]
    gap = np.zeros((2, int(0.4 * A.SR)))
    x = np.concatenate(sum([[p, gap] for p in parts], [])[:-1], 1)
    A.write(M / "moods-sampler.wav", A.master(x, lufs_like_db=-16))
    to_m4a(M / "moods-sampler.wav")


def intro_video(video=gs_env.RENDER / "intro" / "videos" / "intro" / "480p15" / "Intro.mp4",
                out=gs_env.BRAND / "templates" / "intro-preview-480p.mp4"):
    out.parent.mkdir(parents=True, exist_ok=True)
    dur = sf.info(str(M / "intro-sting.wav")).duration
    subprocess.run([gs_env.FFMPEG, "-v", "error", "-y", "-i", str(video), "-i", str(M / "intro-sting.wav"),
                    "-vf", "tpad=stop_mode=clone:stop_duration=1", "-t", f"{dur:.2f}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(out)], check=True)


if __name__ == "__main__":
    sample_30s()
    moods()
    intro_video()
    print("ok")
