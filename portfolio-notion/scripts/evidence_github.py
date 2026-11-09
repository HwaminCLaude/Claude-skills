"""Evidence gathering: inventory GitHub accounts and pull every numeric claim from their READMEs.
Usage: python evidence_github.py <user> [<user> ...]   (needs `gh` authenticated)
Writes evidence/github_inventory.json and evidence/github_inventory.md (repo table + numeric README lines).
Only numbers that appear here (or in files you open) may be used in the portfolio."""
import json
import os
import re
import subprocess
import sys
import urllib.request

OUT = os.path.join(os.environ.get("PORTFOLIO_DIR") or os.getcwd(), "evidence")
os.makedirs(OUT, exist_ok=True)
NUM = re.compile(r"\d[\d,\.]*\s?(%|→|->|배|건|명|회|편|개|ms|s\b|초|GB|MB|KB|pt|x\b|배속|점|시간)")


def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True, encoding="utf-8")
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None


def raw(owner, repo, branch, path):
    try:
        with urllib.request.urlopen(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}", timeout=60) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return ""


inv, md = {}, ["# GitHub evidence inventory", ""]
for user in sys.argv[1:]:
    repos = gh(f"users/{user}/repos?per_page=100&type=owner&sort=created") or []
    inv[user] = []
    md += [f"## {user} ({len(repos)} repos)", "", "| repo | fork | lang | created | pushed | KB | description |", "|---|---|---|---|---|---|---|"]
    for r in repos:
        row = {k: r.get(k) for k in ("name", "fork", "language", "created_at", "pushed_at", "size", "description", "default_branch", "homepage", "topics")}
        md.append(f"| {row['name']} | {row['fork']} | {row['language'] or '-'} | {row['created_at'][:10]} | {row['pushed_at'][:10]} | {row['size']} | {(row['description'] or '-')[:90]} |")
        if not r.get("fork"):
            readme = raw(user, r["name"], r["default_branch"], "README.md") or raw(user, r["name"], r["default_branch"], "readme.md")
            lines = [l.strip() for l in readme.splitlines() if NUM.search(l)]
            row["readme_numeric_lines"] = lines[:60]
            row["readme_chars"] = len(readme)
        inv[user].append(row)
    md.append("")
    for row in inv[user]:
        if row.get("readme_numeric_lines"):
            md += [f"### {user}/{row['name']} - numeric lines in README", ""] + [f"- {l[:220]}" for l in row["readme_numeric_lines"]] + [""]
with open(os.path.join(OUT, "github_inventory.json"), "w", encoding="utf-8") as f:
    json.dump(inv, f, ensure_ascii=False, indent=1)
with open(os.path.join(OUT, "github_inventory.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print(f"wrote {OUT}/github_inventory.md ({sum(len(v) for v in inv.values())} repos)")
