"""Back up the studio code (not the venv / models / renders) into the synced project folder.

    python backup_code.py
The studio folder is not synced; this copies scripts/, templates/ and episodes/*/ (*.py, *.md) plus studio.toml
to [paths] backup (default <project>/studio-code-backup) so a new computer can be rebuilt from the synced folder.
"""
import shutil

import gs_env

DEST = gs_env.Path(gs_env.cfg("paths", "backup", "") or gs_env.PROJECT / "studio-code-backup")


def main():
    n = 0
    for sub in ["scripts", "templates", "episodes"]:
        for p in (gs_env.STUDIO / sub).rglob("*"):
            if p.is_file() and p.suffix in (".py", ".md", ".ass", ".txt") and "__pycache__" not in p.parts:
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
