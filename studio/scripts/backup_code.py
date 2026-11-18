"""Back up the studio's code and settings (not the Python environment, models or renders) into the project folder.

    python backup_code.py
The studio folder is not synced; this copies scripts/, templates/, requirements/, episodes/*/ and shorts/*/ (edl.py,
edl_auto.py), web/kit/ (your house style, intro, drawing pieces) and web/ep/ (every piece's animation modules) plus
studio.toml to [paths] backup (default <project>/studio-code-backup), so a new computer can be rebuilt from the
project folder. Photos and other large files in web/ep/*/assets are not copied: keep their originals in the project.
"""
import shutil

import gs_env

DEST = gs_env.Path(gs_env.cfg("paths", "backup", "") or gs_env.PROJECT / "studio-code-backup")
KEEP = (".py", ".md", ".ass", ".txt", ".js", ".mjs", ".json", ".css", ".toml")


def main():
    n = 0
    for sub in ["scripts", "templates", "requirements", "episodes", "shorts", "web/kit", "web/ep"]:
        root = gs_env.STUDIO / sub
        for p in root.rglob("*") if root.exists() else []:
            if p.is_file() and p.suffix in KEEP and "__pycache__" not in p.parts and "node_modules" not in p.parts:
                out = DEST / p.relative_to(gs_env.STUDIO)
                out.parent.mkdir(parents=True, exist_ok=True)
                if not out.exists() or out.stat().st_mtime < p.stat().st_mtime:
                    shutil.copy2(p, out)
                    n += 1
    if gs_env.CONFIG_FILE.exists():
        DEST.mkdir(parents=True, exist_ok=True)
        shutil.copy2(gs_env.CONFIG_FILE, DEST / "studio.toml")
    print(f"backed up {n} changed file(s) to {DEST}")


if __name__ == "__main__":
    main()
