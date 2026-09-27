"""Generate the README architecture as version-controlled SVG and PNG."""
import html
from pathlib import Path

from playwright.sync_api import sync_playwright

out = Path("docs/images")
out.mkdir(parents=True, exist_ok=True)
parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="1080" viewBox="0 0 1440 1080">',
         '<rect width="1440" height="1080" fill="#101513"/>',
         '<style>text{font-family:Arial,sans-serif;fill:#edf3ed}.sub{fill:#a7b9aa;font-size:16px}.label{fill:#bcf781;font-size:12px;letter-spacing:2px}</style>',
         '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#849c78"/></marker></defs>']
def text(x, y, value, size=20, cls=""):
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}" class="{cls}">{html.escape(value)}</text>')
def box(x,y,w,h,title,subtitle):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#1b251e" stroke="#425840"/>')
    text(x+20,y+32,title,20)
    text(x+20,y+59,subtitle,16,"sub")
def line(x1,y1,x2,y2):
    parts.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="#849c78" stroke-width="2" fill="none" marker-end="url(#arrow)"/>')
text(60,55,"MULTI-AGENT DATA RELIABILITY LAB",14,"label")
text(60,104,"Evidence before action.",40)
text(60,137,"Implemented architecture • local application • optional BYOK or local inference",18,"sub")
box(60,185,390,90,"CLI + FastAPI + local UI","Idempotent runs / persistent job queue")
box(520,185,390,90,"Context and evidence collector","Contract / source manifest / SQL / lineage")
box(980,185,400,90,"Model transport","HTTP endpoint or host-only Codex eval")
line(450,230,520,230)
text(60,323,"STATEFUL LANGGRAPH WORKFLOW",12,"label")
box(60,350,270,90,"Planning agent","Typed investigation questions")
box(410,330,285,85,"Data investigator","Completeness and data profile")
box(410,455,285,85,"Code investigator","SQL grain and semantics")
box(770,385,285,90,"Evidence reviewer","Citations / uncertainty / decision")
box(1120,385,260,90,"Repair proposer","Candidate SQL only")
line(330,395,410,372)
line(330,395,410,497)
line(695,372,770,420)
line(695,497,770,440)
line(1055,430,1120,430)
line(1250,475,1250,625)
box(60,625,390,100,"Persisted state + artifact store","SQLite WAL / checkpoints / hashes")
box(520,625,390,100,"Deterministic verification","Incident + three regression snapshots")
box(980,625,400,100,"Restricted SQL subprocess","AST allowlist / no external I/O / timeout")
line(980,675,910,675)
line(520,675,450,675)
line(180,440,180,625)
text(60,780,"INSPECTION AND DELIVERY",12,"label")
box(60,810,390,100,"Evidence bundle","JSON / Markdown / SQL patch / diff")
box(520,810,390,100,"Observability","Local events / OTel traces / metrics")
box(980,810,400,100,"Evaluation harness","Single vs multi / controls / failures")
line(255,725,255,810)
line(715,725,715,810)
text(60,979,"GATES",12,"label")
text(150,979,"Missing records or semantics → abstain. Failed checks → reject. No source mutation.",18,"sub")
text(60,1025,"Demo policies are scripted. Live model results are reported separately. SQL-first synthetic scope.",16,"sub")
parts.append("</svg>")
svg = out / "architecture.svg"
svg.write_text("".join(parts), encoding="utf-8")
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width":1440,"height":1080})
    page.goto(svg.resolve().as_uri())
    page.screenshot(path=str(out / "architecture.png"))
    browser.close()
print("Architecture SVG and PNG rendered.")

