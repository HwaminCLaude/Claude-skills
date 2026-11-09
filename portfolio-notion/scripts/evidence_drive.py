"""Evidence gathering: summarize Google Drive folders through rclone (read-only).
Usage: python evidence_drive.py <remote:> <folder> [<folder> ...] [--depth 2]
Writes evidence/drive_tree.md with per-folder file counts and the first entries (path;size;mime),
and prints small text/markdown files (<64KB) named README*.md, *설계*.md, *.txt so numbers can be quoted."""
import os
import subprocess
import sys

args = [a for a in sys.argv[1:] if not a.startswith("--")]
depth = next((int(sys.argv[i + 1]) for i, a in enumerate(sys.argv) if a == "--depth"), 2)
remote, folders = args[0], args[1:]
OUT = os.path.join(os.environ.get("PORTFOLIO_DIR") or os.getcwd(), "evidence")
os.makedirs(OUT, exist_ok=True)


def rclone(*a):
    r = subprocess.run(["rclone", *a], capture_output=True, text=True, encoding="utf-8")
    return r.stdout


md = ["# Google Drive evidence", ""]
for folder in folders:
    path = f"{remote}{folder}"
    files = [l for l in rclone("lsf", path, "-R", "--files-only").splitlines() if l]
    tree = rclone("lsf", path, "-R", "--max-depth", str(depth), "--format", "psm").splitlines()
    md += [f"## {folder} ({len(files)} files)", "", "```"] + tree[:80] + ["```", ""]
    for f in files:
        name = f.rsplit("/", 1)[-1]
        if name.lower().startswith("readme") or "설계" in name or name.endswith(".txt"):
            size = rclone("size", f"{path}/{f}", "--json")
            if '"bytes":' in size and int(size.split('"bytes":')[1].split(",")[0].strip(" }\n")) < 65536:
                md += [f"### {folder}/{f}", "", "```"] + rclone("cat", f"{path}/{f}").splitlines()[:200] + ["```", ""]
with open(os.path.join(OUT, "drive_tree.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(md))
print(f"wrote {OUT}/drive_tree.md")
