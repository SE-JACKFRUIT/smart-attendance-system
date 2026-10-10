"""Creates one GitHub Issue per user story in BACKLOG.md using the GitHub CLI.

Usage (after `gh auth login` and `gh repo set-default`):
    python tools/create_issues.py --dry-run     # just print what would happen
    python tools/create_issues.py               # really create them

Each issue gets: title 'US-xx: ...', the story text + acceptance criteria as
body, labels from the story, and is assigned to you (@me).
Labels must already exist (create them first, or pass --create-labels).
"""
import re
import subprocess
import sys
from pathlib import Path

text = (Path(__file__).resolve().parent.parent / "BACKLOG.md").read_text(encoding="utf-8")
dry = "--dry-run" in sys.argv
make_labels = "--create-labels" in sys.argv

stories = re.split(r"\n(?=### US-)", text)[1:]
all_labels = set()
parsed = []
for block in stories:
    block = block.split("\n---")[0].split("\n## Turning")[0].strip()
    head, body = block.split("\n", 1)
    m = re.match(r"### (US-\d+) — (.+)", head)
    num, title = m.group(1), m.group(2).strip()
    labels = re.findall(r"`([^`]+)`", body.split("Labels:")[-1]) if "Labels:" in body else []
    points = re.search(r"Story points: (\d+)", body)
    body = body.replace("Labels:", "\nLabels:")
    parsed.append((f"{num}: {title}", body.strip(), labels, points.group(1) if points else "?"))
    all_labels.update(labels)

if make_labels:
    for lab in sorted(all_labels):
        cmd = ["gh", "label", "create", lab, "--force"]
        print(" ".join(cmd))
        if not dry:
            subprocess.run(cmd, check=False)

for title, body, labels, pts in parsed:
    cmd = ["gh", "issue", "create", "--title", title, "--body", body, "--assignee", "@me"]
    for lab in labels:
        cmd += ["--label", lab]
    print(f"{title}  [{pts} pts]  labels={labels}")
    if not dry:
        subprocess.run(cmd, check=True)
print(f"\n{len(parsed)} stories", "(dry run)" if dry else "created")
