"""Render a labeled results figure from committed evaluation rows."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

image = Image.new("RGB", (1400, 850), "#0c151c")
draw = ImageDraw.Draw(image)


def label(position, text, size=24, fill="#c6d4dd"):
    draw.text(position, text, font=ImageFont.load_default(size=size), fill=fill)


label((60, 45), "MULTI-AGENT DATA RELIABILITY LAB", 38, "#bcf781")
label((60, 103), "Recorded outcomes | Synthetic commerce incidents", 27)
label((60, 163), "Expected outcome", 20, "#bcf781")
label((370, 163), "Failed inference", 20, "#ffb47b")
entries = []
for folder, mode in (("demo", "Scripted demo"), ("headless", "Live headless")):
    report = json.loads(Path(f"docs/evals/{folder}/results.json").read_text())
    for topology in ("single", "multi"):
        rows = [r for r in report["rows"] if r["topology"] == topology]
        entries.append((f"{mode} / {topology}", rows))
for i, (name, rows) in enumerate(entries):
    y = 235 + i * 100
    correct = sum(r["outcome_correct"] for r in rows)
    failed = sum(r["outcome"] == "failed" for r in rows)
    label((60, y), name, 24)
    left, width = 420, 700
    draw.rounded_rectangle((left, y, left + width, y + 35), radius=5, fill="#263744")
    draw.rectangle((left, y, left + width * correct / len(rows), y + 35), fill="#bcf781")
    if failed:
        draw.rectangle((left + width * correct / len(rows), y, left + width, y + 35), fill="#ffb47b")
    label((1150, y), f"{correct}/{len(rows)}", 27)
label((60, 680), "Demo: zero model calls. Authored policies; not a model accuracy benchmark.", 24)
label((60, 725), "Live: unpinned CLI model; four inference failures. No architecture ranking.", 24)
label((60, 770), "Source: docs/evals/{demo,headless}/results.json | 2026-09-27", 21, "#8c9eaa")
image.save("docs/images/evaluation.png")
