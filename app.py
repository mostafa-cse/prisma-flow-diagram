"""
PRISMA 2020 Flow Diagram — Flask Web App
  + User authentication (sign-up / sign-in)
  + Per-user diagram history stored in SQLite
"""

import io
import os
import glob
import json
import base64
import sqlite3
import functools
from datetime import datetime

# matplotlib globals — populated lazily on first use to avoid crashing
# the Vercel serverless function at cold-start import time.
plt         = None
mpatches    = None
FancyBboxPatch = None
PdfPages    = None

def _setup_matplotlib():
    """Import matplotlib and populate module-level stubs (once)."""
    global plt, mpatches, FancyBboxPatch, PdfPages
    if plt is not None:
        return  # already imported
    # On Vercel (read-only FS except /tmp) redirect matplotlib's config dir
    if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        os.makedirs("/tmp/matplotlib", exist_ok=True)
        os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as _plt
    import matplotlib.patches as _mpatches
    from matplotlib.patches import FancyBboxPatch as _FancyBboxPatch
    from matplotlib.backends.backend_pdf import PdfPages as _PdfPages
    plt          = _plt
    mpatches     = _mpatches
    FancyBboxPatch = _FancyBboxPatch
    PdfPages     = _PdfPages

from werkzeug.security import generate_password_hash, check_password_hash
from flask import (Flask, render_template, request, send_file,
                   send_from_directory, session, redirect, url_for, g)

app = Flask(__name__)
app.secret_key = "prisma_2020_secret_key_systematic_review_x9z"

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
# On Vercel serverless the filesystem is read-only except /tmp.
# Use /tmp for the SQLite DB so init_db() can write.
if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
    DATABASE = "/tmp/prisma_users.db"
else:
    DATABASE = os.path.join(BASE_DIR, "prisma_users.db")
IMAGES_DIR     = os.path.join(BASE_DIR, "Systematic Review images")
DIFF_STYLE_DIR = os.path.join(BASE_DIR, "Different Style ")
GEN_STYLE_DIR  = os.path.join(BASE_DIR, "Generated Styles")

# ── Visual styles for generated diagrams (color + full structure) ──────────────────────────────────────────────────────
DIAGRAM_STYLES = {
    "classic": {
        "name": "Classic Blue",       "bg_col": "white",
        "boxstyle": "round,pad=0.03",  "box_lw": 1.3,  "arrow_lw": 1.3,
        "box_fg": "#f0f7ff",  "box_edge": "#2c3e50",
        "inc_fg": "#d0eaff",  "inc_edge": "#1a6fa0",  "inc_lw": 2.0,
        "side_fg": "white",   "side_edge": "#2c3e50",
        "text_col": "#222222", "title_col": "#1a3a5c", "arrow_col": "#2c3e50",
        "shadow": False, "phase_bands": False,
    },
    "academic": {
        "name": "Academic Square",    "bg_col": "white",
        "boxstyle": "square,pad=0.04", "box_lw": 2.0,  "arrow_lw": 1.6,
        "box_fg": "#ffffff",  "box_edge": "#111111",
        "inc_fg": "#f5f5ff",  "inc_edge": "#111111",  "inc_lw": 2.5,
        "side_fg": "#fffde7", "side_edge": "#888800",
        "text_col": "#111111", "title_col": "#111111", "arrow_col": "#111111",
        "shadow": False, "phase_bands": True,
        "phase_cols": ["#1565c0", "#2e7d32", "#e65100", "#6a1b9a", "#00695c"],
    },
    "colorful": {
        "name": "Colorful Phases",    "bg_col": "#f8faff",
        "boxstyle": "round,pad=0.04", "box_lw": 1.8,  "arrow_lw": 1.5,
        "box_fg": "#e3f2fd",  "box_edge": "#1565c0",
        "inc_fg": "#e8f5e9",  "inc_edge": "#2e7d32",  "inc_lw": 2.5,
        "side_fg": "#fff3e0", "side_edge": "#e65100",
        "text_col": "#1a1a2e", "title_col": "#1a237e", "arrow_col": "#455a64",
        "shadow": False, "phase_bands": False,
        "phase_box_cols": [
            {"fg": "#e3f2fd", "edge": "#1565c0"},
            {"fg": "#fff9c4", "edge": "#f57f17"},
            {"fg": "#ffe0b2", "edge": "#e65100"},
            {"fg": "#f3e5f5", "edge": "#7b1fa2"},
        ],
    },
    "minimal": {
        "name": "Minimal Outline",    "bg_col": "white",
        "boxstyle": "square,pad=0.02", "box_lw": 0.75, "arrow_lw": 0.9,
        "box_fg": "white",    "box_edge": "#888888",
        "inc_fg": "#f5f5f5",  "inc_edge": "#333333",  "inc_lw": 1.3,
        "side_fg": "white",   "side_edge": "#bbbbbb",
        "text_col": "#333333", "title_col": "#333333", "arrow_col": "#666666",
        "shadow": False, "phase_bands": False,
    },
    "bold_navy": {
        "name": "Bold Navy",           "bg_col": "#e8eeff",
        "boxstyle": "round,pad=0.04",  "box_lw": 0.5,  "arrow_lw": 1.8,
        "box_fg": "#1a3a6a",  "box_edge": "#0a2040",
        "inc_fg": "#0a5f8a",  "inc_edge": "#04315a",  "inc_lw": 2.0,
        "side_fg": "#2e4a80", "side_edge": "#0a2040",
        "text_col": "#ffffff", "title_col": "#0a2040", "arrow_col": "#1a3a6a",
        "shadow": False, "phase_bands": False,
    },
    "shadowed": {
        "name": "Shadowed Cards",      "bg_col": "#eef0f4",
        "boxstyle": "round,pad=0.04",  "box_lw": 1.0,  "arrow_lw": 1.3,
        "box_fg": "#ffffff",  "box_edge": "#b0bcd0",
        "inc_fg": "#e8f4fd",  "inc_edge": "#1a6fa0",  "inc_lw": 2.0,
        "side_fg": "#ffffff", "side_edge": "#c0c8d4",
        "text_col": "#1a2a40", "title_col": "#1a2a40", "arrow_col": "#4a5a70",
        "shadow": True, "phase_bands": False,
    },
    "green": {
        "name": "Forest Green",        "bg_col": "#f0fff5",
        "boxstyle": "round,pad=0.03",  "box_lw": 1.5,  "arrow_lw": 1.3,
        "box_fg": "#e8f8ee",  "box_edge": "#1a6a38",
        "inc_fg": "#c3f0d0",  "inc_edge": "#0d5228",  "inc_lw": 2.0,
        "side_fg": "#f0ffe8", "side_edge": "#3a8a50",
        "text_col": "#0a2010", "title_col": "#1a4a28", "arrow_col": "#1a6a38",
        "shadow": False, "phase_bands": False,
    },
    "warm": {
        "name": "Warm Amber",          "bg_col": "#fffef0",
        "boxstyle": "round,pad=0.03",  "box_lw": 1.5,  "arrow_lw": 1.3,
        "box_fg": "#fff8e8",  "box_edge": "#c05800",
        "inc_fg": "#ffe5b8",  "inc_edge": "#a84000",  "inc_lw": 2.0,
        "side_fg": "#fff3d8", "side_edge": "#d07000",
        "text_col": "#3a1800", "title_col": "#6a2800", "arrow_col": "#c05800",
        "shadow": False, "phase_bands": False,
    },
    "corporate": {
        "name": "Corporate",           "bg_col": "#f7f8fb",
        "boxstyle": "square,pad=0.04", "box_lw": 1.5,  "arrow_lw": 1.5,
        "box_fg": "#eef0f8",  "box_edge": "#2a3460",
        "inc_fg": "#dce4f5",  "inc_edge": "#1a2450",  "inc_lw": 2.5,
        "side_fg": "#e8eafa", "side_edge": "#505a80",
        "text_col": "#1a2040", "title_col": "#1a2040", "arrow_col": "#2a3460",
        "shadow": True, "phase_bands": True,
        "phase_cols": ["#2a3460", "#1a5a8a", "#1a6a50", "#5a2a7a", "#1a6a38"],
    },
    "purple": {
        "name": "Royal Purple",        "bg_col": "#faf0ff",
        "boxstyle": "round,pad=0.03",  "box_lw": 1.5,  "arrow_lw": 1.3,
        "box_fg": "#f5e8ff",  "box_edge": "#6a1a9a",
        "inc_fg": "#e0c8ff",  "inc_edge": "#4a0a7a",  "inc_lw": 2.0,
        "side_fg": "#f8f0ff", "side_edge": "#8a3ac0",
        "text_col": "#2a0a40", "title_col": "#3a0a60", "arrow_col": "#6a1a9a",
        "shadow": False, "phase_bands": False,
    },
    "teal": {
        "name": "Ocean Teal",          "bg_col": "#f0fbfb",
        "boxstyle": "round,pad=0.03",  "box_lw": 1.5,  "arrow_lw": 1.3,
        "box_fg": "#e0f5f5",  "box_edge": "#1a7a7a",
        "inc_fg": "#c0eeee",  "inc_edge": "#0a6060",  "inc_lw": 2.0,
        "side_fg": "#eaf8f8", "side_edge": "#2a9090",
        "text_col": "#0a2828", "title_col": "#0a4848", "arrow_col": "#1a7a7a",
        "shadow": False, "phase_bands": False,
    },
    "orange_flow": {
        "name": "Orange Flow",          "bg_col": "white",
        "boxstyle": "square,pad=0.03",  "box_lw": 1.2,  "arrow_lw": 1.0,
        "box_fg": "#ffffff",  "box_edge": "#333333",
        "inc_fg": "#fff8f0",  "inc_edge": "#e8960c",  "inc_lw": 2.0,
        "side_fg": "#ffffff", "side_edge": "#333333",
        "text_col": "#111111", "title_col": "#e8960c", "arrow_col": "#333333",
        "shadow": False, "phase_bands": True,
        "phase_cols": ["#2196f3", "#2196f3", "#2196f3", "#2196f3", "#e8960c"],
        "font_scale": 1.0,
    },
}
STYLE_KEYS = list(DIAGRAM_STYLES.keys())

# ── Explicit mapping: source label → style key ────────────────────────────────
SOURCE_TO_STYLE = {
    "Souce 10":  "orange_flow",
    "Source 01": "academic",
    "Source 02": "colorful",
    "Source 03": "minimal",
    "Source 04": "bold_navy",
    "Source 05": "shadowed",
    "Source 06": "green",
    "Source 07": "warm",
    "Source 08": "corporate",
    "Source 09": "purple",
    "Soure 11":  "teal",
}

# ──────────────────────────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS diagrams (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            title      TEXT,
            img_b64    TEXT    NOT NULL,
            form_data  TEXT    NOT NULL,
            created_at TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    db.commit()

    # Seed a demo account if it doesn't exist yet
    existing = db.execute("SELECT id FROM users WHERE username = 'demo'").fetchone()
    if not existing:
        from werkzeug.security import generate_password_hash as _gph
        db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            ("demo", "demo@gmail.com", _gph("demo1234"))
        )
        db.commit()

    db.close()


# ──────────────────────────────────────────────────────────────────────────────
# Auth decorator
# ──────────────────────────────────────────────────────────────────────────────

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────────────────────────────────────
# Diagram generator
# ──────────────────────────────────────────────────────────────────────────────

def draw_box(ax, x, y, w, h, lines, facecolor="white", edgecolor="#2c3e50",
             lw=1.3, text_col="#333333", st=None, accent_col=None):
    """Draw a styled PRISMA box with shadow, optional left accent bar, and text."""
    bs = st["boxstyle"] if st else "round,pad=0.05"
    # Drop shadow — stronger when style requests it, always subtle
    sh_alpha = 0.40 if (st and st.get("shadow")) else 0.18
    sh_col   = "#7a8fa8" if (st and st.get("shadow")) else "#b0c0cc"
    sp = FancyBboxPatch(
        (x - w/2 + 0.10, y - h/2 - 0.12), w, h,
        boxstyle=bs, linewidth=0, facecolor=sh_col, alpha=sh_alpha, zorder=2)
    ax.add_patch(sp)
    # Main box
    box = FancyBboxPatch(
        (x - w/2, y - h/2), w, h,
        boxstyle=bs, linewidth=lw, edgecolor=edgecolor, facecolor=facecolor, zorder=3)
    ax.add_patch(box)
    # Colored left accent bar (inset slightly to avoid corner artifacts)
    if accent_col:
        bar_w = min(0.22, w * 0.068)
        bar = plt.Rectangle(
            (x - w/2 + 0.006, y - h/2 + 0.012), bar_w, h - 0.024,
            facecolor=accent_col, edgecolor="none", zorder=4)
        ax.add_patch(bar)
    # Text
    n    = len(lines)
    step = h / (n + 1)
    for i, (txt, bold, fs) in enumerate(lines):
        ty = y + h/2 - step * (i + 1)
        ax.text(x, ty, txt, ha="center", va="center",
                fontsize=fs, fontweight="bold" if bold else "normal",
                color=text_col, zorder=5)


def darrow(ax, x1, y1, x2, y2, color="#2c3e50", lw=1.3):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=lw, mutation_scale=17), zorder=2)


def hline(ax, x1, x2, y, color="#2c3e50", lw=1.3):
    ax.plot([x1, x2], [y, y], color=color, lw=lw, zorder=2)


def generate_diagram(d):
    """Three-pathway PRISMA 2020 Flow Diagram.

    Streams
    ───────
    • Left   — Previous Studies (identification → straight to Y_INC)
    • Centre — Databases / Registers (full pipeline: pre-screening → screened
                → sought → assessed → included)
    • Right  — Other Methods (identified → sought → assessed → included)

    All three streams converge into a single "Total Studies Included" box,
    which then fans out into up to two parallel analytical branches.

    Every text element uses the same Uniform Font Size (UFS = 8.0 × font_scale)
    so that no box appears to have larger or smaller text than any other.
    """
    _setup_matplotlib()   # ensure matplotlib is imported before use
    # ── Style resolution ──────────────────────────────────────────────────────
    style_key = d.get("style", "classic")
    st  = DIAGRAM_STYLES.get(style_key, DIAGRAM_STYLES["classic"])
    bg  = st.get("bg_col", "white")
    TC  = st.get("text_col", "#222222")
    ALW = max(2.0, st.get("arrow_lw", 1.5) * 1.30)   # bolder arrows
    AC  = st["arrow_col"]
    FS  = st.get("font_scale", 1.0)
    UFS = 14.0 * FS     # Uniform font size — every text element uses this

    # ── Stream identity accent colors ─────────────────────────────────────────
    PREV_ACC  = "#6c5ce7"       # violet  — Previous Studies
    DB_ACC    = st["box_edge"]  # primary — Databases / Registers
    OTHER_ACC = "#e07b54"       # burnt orange — Other Methods
    INC_ACC   = "#00a878"       # teal green — Included / Total boxes
    SIDE_ACC  = "#d63031"       # red — Exclusion side boxes

    # per-phase box colours (colorful style)
    pbc = st.get("phase_box_cols")
    def mfg(i):   return pbc[i]["fg"]   if pbc and i < len(pbc) else st["box_fg"]
    def medge(i): return pbc[i]["edge"] if pbc and i < len(pbc) else st["box_edge"]

    # ── Canvas ─────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(22, 22))
    ax.set_xlim(0, 22); ax.set_ylim(0, 22); ax.axis("off")
    fig.patch.set_facecolor(bg); ax.set_facecolor(bg)

    # ── Column geometry ────────────────────────────────────────────────────────
    #                    centre   width
    PX,  PW  = 2.0,   3.2   # Previous Studies (left)
    DX,  DW  = 8.5,   4.8   # Databases / Registers (centre)
    OX,  OW  = 16.8,  3.5   # Other Methods (right)
    DEX, DEW = 13.0,  3.5   # DB side exclusion boxes
    OEX, OEW = 20.7,  2.5   # Other-Methods side exclusion boxes
    TX,  TW  = 11.0,  6.5   # Total Included (centred)

    # ── Vertical positions (top → bottom) ─────────────────────────────────────
    Y_ID  = 20.0    # Identification row
    Y_PRE = 18.0    # Pre-screening removal (DB side)
    Y_SC  = 15.8    # Screened (DB only)
    Y_SCX = 14.0    # Screened exclusions (DB side)
    Y_SOU = 12.0    # Sought for retrieval (DB + Other)
    Y_NR  = 10.6    # Not retrieved (DB side + Other side)
    Y_ASS = 9.0     # Assessed for eligibility (DB + Other)
    Y_EX  = 7.3     # Eligibility exclusions (DB side + Other side)
    Y_INC = 5.5     # Included per stream (all 3 columns)
    Y_TOT = 3.5     # Total included
    Y_AN  = 1.3     # Analysis branches

    H_STD = 0.75    # Standard single-line box height

    # ══════════════════════════════════════════════════════════════════════════
    # STREAM COLUMN HEADER BANNERS
    # ══════════════════════════════════════════════════════════════════════════
    HDR_Y, HDR_H = 21.15, 0.44
    for (hx, hw, label, hcol) in [
        (PX,  PW,  "PREVIOUS STUDIES",      PREV_ACC),
        (DX,  DW,  "DATABASES / REGISTERS", DB_ACC),
        (OX,  OW,  "OTHER METHODS",         OTHER_ACC),
    ]:
        hdr = FancyBboxPatch(
            (hx - hw/2, HDR_Y - HDR_H/2), hw, HDR_H,
            boxstyle="round,pad=0.06",
            facecolor=hcol, edgecolor="none", alpha=0.92, zorder=5)
        ax.add_patch(hdr)
        ax.text(hx, HDR_Y, label, ha="center", va="center",
                fontsize=UFS * 0.58, fontweight="bold", color="white", zorder=6)

    # ══════════════════════════════════════════════════════════════════════════
    # IDENTIFICATION ROW
    # ══════════════════════════════════════════════════════════════════════════

    # ── Previous Studies (left) ───────────────────────────────────────────────
    prev_n = d.get("prev_included", "0") or "0"
    h_prev = H_STD
    draw_box(ax, PX, Y_ID, PW, h_prev,
             [("Studies from previous version", False, UFS),
              (f"of review (n = {prev_n})", False, UFS)],
             facecolor=mfg(0), edgecolor=medge(0), lw=st["box_lw"], text_col=TC, st=st,
             accent_col=PREV_ACC)

    # ── Databases / Registers (centre) ───────────────────────────────────────
    db_id   = d.get("db_identified", d.get("total_identified", "0")) or "0"
    db_lines = []
    for i in range(1, 7):
        nm = d.get(f"db{i}_name", "").strip()
        vl = d.get(f"db{i}_count", "").strip()
        if nm and vl:
            db_lines.append(f"  \u2022 {nm}: {vl}")
    db_id_rows  = [(f"Records identified from databases (n = {db_id}):", True, UFS)]
    db_id_rows += [(ln, False, UFS) for ln in db_lines]
    h_db_id     = max(H_STD, 0.28 * len(db_id_rows) + 0.4)
    draw_box(ax, DX, Y_ID, DW, h_db_id, db_id_rows,
             facecolor=mfg(0), edgecolor=medge(0), lw=st["box_lw"], text_col=TC, st=st,
             accent_col=DB_ACC)

    # ── Other Methods (right) ─────────────────────────────────────────────────
    other_id = d.get("other_identified", d.get("other_id_total", "0")) or "0"
    draw_box(ax, OX, Y_ID, OW, H_STD,
             [("Records from other methods", False, UFS),
              (f"(n = {other_id})", False, UFS)],
             facecolor=mfg(0), edgecolor=medge(0), lw=st["box_lw"], text_col=TC, st=st,
             accent_col=OTHER_ACC)

    # ══════════════════════════════════════════════════════════════════════════
    # PRE-SCREENING REMOVAL (DB side box only)
    # ══════════════════════════════════════════════════════════════════════════
    db_dup    = d.get("db_duplicates", d.get("duplicates", "0")) or "0"
    db_auto   = d.get("db_automation_exc", d.get("auto_excluded", "")).strip()
    db_oth_ex = d.get("db_other_exc",      d.get("other_removed", "")).strip()
    pre_rows  = [(f"Records removed before screening:", True,  UFS),
                 (f"  \u2022 Duplicates (n = {db_dup})", False, UFS)]
    if db_auto:
        pre_rows.append((f"  \u2022 Automation tools (n = {db_auto})", False, UFS))
    if db_oth_ex:
        pre_rows.append((f"  \u2022 Other reasons (n = {db_oth_ex})", False, UFS))
    h_pre = max(0.9, 0.28 * len(pre_rows) + 0.3)
    draw_box(ax, DEX, Y_PRE, DEW, h_pre, pre_rows,
             facecolor=st["side_fg"], edgecolor=st["side_edge"],
             lw=st["box_lw"], text_col=TC, st=st, accent_col=SIDE_ACC)

    # ══════════════════════════════════════════════════════════════════════════
    # SCREENED  (DB centre column only)
    # ══════════════════════════════════════════════════════════════════════════
    db_sc = d.get("db_screened", d.get("screened", "0")) or "0"
    sc_rows = [(f"Records screened (n = {db_sc})", True, UFS)]
    # Conflict breakdown (optional)
    sc_inc   = d.get("sc_included",   "").strip()
    sc_exc   = d.get("sc_excluded",   "").strip()
    conf_tot = d.get("conflict_total","").strip()
    if sc_inc:
        sc_rows.append((f"  \u2022 Agreed — Included: {sc_inc}", False, UFS))
    if sc_exc:
        sc_rows.append((f"  \u2022 Agreed — Excluded: {sc_exc}", False, UFS))
    if conf_tot and conf_tot != "0":
        sc_rows += [
            (f"  \u2022 Conflicts (n = {conf_tot}):", False, UFS),
            (f"       \u25e6 Included after discussion: {d.get('conflict_inc','0')}", False, UFS),
            (f"       \u25e6 Excluded after discussion: {d.get('conflict_exc','0')}", False, UFS),
        ]
    h_sc = max(H_STD, 0.28 * len(sc_rows) + 0.3)
    draw_box(ax, DX, Y_SC, DW, h_sc, sc_rows,
             facecolor=mfg(1), edgecolor=medge(1), lw=st["box_lw"], text_col=TC, st=st,
             accent_col=DB_ACC)

    # Screened exclusions side box (DB)  — EX1-EX6 coded reasons
    db_exc_sc  = d.get("db_exc_screened", d.get("exc_screened", "0")) or "0"
    scx_rows   = [(f"Records excluded at screening (n = {db_exc_sc})", True, UFS)]
    for i in range(1, 7):
        r = d.get(f"sc_exc_code{i}", "").strip()
        v = d.get(f"sc_exc_code{i}_n", "").strip()
        if r and v:
            scx_rows.append((f"  EX{i}: {r} (n = {v})", False, UFS))
    h_scx = max(H_STD, 0.28 * len(scx_rows) + 0.3)
    draw_box(ax, DEX, Y_SCX, DEW, h_scx, scx_rows,
             facecolor=st["side_fg"], edgecolor=st["side_edge"],
             lw=st["box_lw"], text_col=TC, st=st, accent_col=SIDE_ACC)

    # ══════════════════════════════════════════════════════════════════════════
    # SOUGHT FOR RETRIEVAL  (DB + Other)
    # ══════════════════════════════════════════════════════════════════════════
    db_sou    = d.get("db_sought",    d.get("retrieval", "0")) or "0"
    other_sou = d.get("other_sought", "0") or "0"
    draw_box(ax, DX, Y_SOU, DW, H_STD,
             [(f"Reports sought for retrieval (n = {db_sou})", True, UFS)],
             facecolor=mfg(2), edgecolor=medge(2), lw=st["box_lw"], text_col=TC, st=st,
             accent_col=DB_ACC)
    draw_box(ax, OX, Y_SOU, OW, H_STD,
             [(f"Reports sought (n = {other_sou})", True, UFS)],
             facecolor=mfg(2), edgecolor=medge(2), lw=st["box_lw"], text_col=TC, st=st,
             accent_col=OTHER_ACC)

    # Not-retrieved side boxes
    db_nr    = d.get("db_not_retrieved",    d.get("not_retrieved", "0")) or "0"
    other_nr = d.get("other_not_retrieved", "") or ""
    draw_box(ax, DEX, Y_NR, DEW, H_STD,
             [(f"Reports not retrieved (n = {db_nr})", False, UFS)],
             facecolor=st["side_fg"], edgecolor=st["side_edge"],
             lw=st["box_lw"], text_col=TC, st=st, accent_col=SIDE_ACC)
    if other_nr:
        draw_box(ax, OEX, Y_NR, OEW, H_STD,
                 [(f"Not retrieved (n = {other_nr})", False, UFS)],
                 facecolor=st["side_fg"], edgecolor=st["side_edge"],
                 lw=st["box_lw"], text_col=TC, st=st, accent_col=SIDE_ACC)

    # ══════════════════════════════════════════════════════════════════════════
    # ASSESSED FOR ELIGIBILITY  (DB + Other)
    # ══════════════════════════════════════════════════════════════════════════
    db_ass    = d.get("db_assessed",    d.get("eligibility", "0")) or "0"
    other_ass = d.get("other_assessed", "0") or "0"
    draw_box(ax, DX, Y_ASS, DW, H_STD,
             [(f"Reports assessed for eligibility (n = {db_ass})", True, UFS)],
             facecolor=mfg(3), edgecolor=medge(3), lw=st["box_lw"], text_col=TC, st=st,
             accent_col=DB_ACC)
    draw_box(ax, OX, Y_ASS, OW, H_STD,
             [(f"Assessed (n = {other_ass})", True, UFS)],
             facecolor=mfg(3), edgecolor=medge(3), lw=st["box_lw"], text_col=TC, st=st,
             accent_col=OTHER_ACC)

    # Eligibility exclusion side boxes  (up to 6 for DB, up to 4 for Other)
    db_exc_ft = d.get("db_exc_reasons_total", d.get("exc_fulltext", "0")) or "0"
    db_ex_rows = [(f"Reports excluded (n = {db_exc_ft})", True, UFS)]
    for i in range(1, 7):
        r = d.get(f"db_exc_reason{i}", d.get(f"exc_reason{i}", "")).strip()
        v = d.get(f"db_exc_reason{i}_n", d.get(f"exc_reason{i}_n", "")).strip()
        if r and v:
            db_ex_rows.append((f"  \u2022 {r}: {v}", False, UFS))
    h_db_ex = max(H_STD, 0.28 * len(db_ex_rows) + 0.3)
    draw_box(ax, DEX, Y_EX, DEW, h_db_ex, db_ex_rows,
             facecolor=st["side_fg"], edgecolor=st["side_edge"],
             lw=st["box_lw"], text_col=TC, st=st, accent_col=SIDE_ACC)

    other_exc_ft = d.get("other_exc_reasons_total", "") or ""
    if other_exc_ft or d.get("other_exc_reason1", "").strip():
        other_ex_rows = [(f"Reports excluded (n = {other_exc_ft or '?'})", True, UFS)]
        for i in range(1, 5):
            r = d.get(f"other_exc_reason{i}", "").strip()
            v = d.get(f"other_exc_reason{i}_n", "").strip()
            if r and v:
                other_ex_rows.append((f"  \u2022 {r}: {v}", False, UFS))
        h_other_ex = max(H_STD, 0.28 * len(other_ex_rows) + 0.3)
        draw_box(ax, OEX, Y_EX, OEW, h_other_ex, other_ex_rows,
                 facecolor=st["side_fg"], edgecolor=st["side_edge"],
                 lw=st["box_lw"], text_col=TC, st=st, accent_col=SIDE_ACC)

    # ══════════════════════════════════════════════════════════════════════════
    # INCLUDED PER STREAM  (all three columns at the same Y)
    # ══════════════════════════════════════════════════════════════════════════
    db_inc    = d.get("db_included",    d.get("included", "0")) or "0"
    other_inc = d.get("other_included", "0") or "0"
    h_inc = H_STD

    # Previous Studies included (left)
    draw_box(ax, PX, Y_INC, PW, h_inc,
             [(f"Previous studies included", False, UFS),
              (f"(n = {prev_n})", False, UFS)],
             facecolor=st["inc_fg"], edgecolor=st["inc_edge"],
             lw=st["inc_lw"], text_col=TC, st=st, accent_col=INC_ACC)

    # DB included (centre)
    draw_box(ax, DX, Y_INC, DW, h_inc,
             [(f"Studies included from databases (n = {db_inc})", True, UFS)],
             facecolor=st["inc_fg"], edgecolor=st["inc_edge"],
             lw=st["inc_lw"], text_col=TC, st=st, accent_col=INC_ACC)

    # Other included (right)
    draw_box(ax, OX, Y_INC, OW, h_inc,
             [(f"Studies from other methods (n = {other_inc})", True, UFS)],
             facecolor=st["inc_fg"], edgecolor=st["inc_edge"],
             lw=st["inc_lw"], text_col=TC, st=st, accent_col=INC_ACC)

    # ══════════════════════════════════════════════════════════════════════════
    # TOTAL INCLUDED (centred merge box)
    # ══════════════════════════════════════════════════════════════════════════
    total_n = d.get("total_included", "0") or "0"
    h_tot   = H_STD
    draw_box(ax, TX, Y_TOT, TW, h_tot,
             [(f"Total studies included in review (n = {total_n})", True, UFS)],
             facecolor=st["inc_fg"], edgecolor=st["inc_edge"],
             lw=st["inc_lw"] + 0.5, text_col=TC, st=st, accent_col=INC_ACC)

    # ══════════════════════════════════════════════════════════════════════════
    # ANALYTICAL BRANCHES (below Total)
    # ══════════════════════════════════════════════════════════════════════════
    an1_txt = d.get("analysis_1_text", "").strip() or "Analysis Branch 1"
    an1_n   = d.get("analysis_1_n",   "").strip()
    an2_txt = d.get("analysis_2_text", "").strip() or "Analysis Branch 2"
    an2_n   = d.get("analysis_2_n",   "").strip()
    an1_label = f"{an1_txt}" + (f"\n(n = {an1_n})" if an1_n else "")
    an2_label = f"{an2_txt}" + (f"\n(n = {an2_n})" if an2_n else "")
    AX1, AX2, AW = 5.5, 16.5, 5.5
    h_an = H_STD
    draw_box(ax, AX1, Y_AN, AW, h_an,
             [(an1_label, False, UFS)],
             facecolor=mfg(3), edgecolor=medge(3), lw=st["box_lw"], text_col=TC, st=st,
             accent_col=INC_ACC)
    draw_box(ax, AX2, Y_AN, AW, h_an,
             [(an2_label, False, UFS)],
             facecolor=mfg(3), edgecolor=medge(3), lw=st["box_lw"], text_col=TC, st=st,
             accent_col=INC_ACC)

    # ══════════════════════════════════════════════════════════════════════════
    # ARROWS — Main flow
    # ══════════════════════════════════════════════════════════════════════════

    # Previous Studies: straight arrow from top box → included box
    darrow(ax, PX, Y_ID  - H_STD/2, PX, Y_INC + H_STD/2,  AC, ALW)

    # DB pipeline arrows (centre column)
    darrow(ax, DX, Y_ID  - h_db_id/2, DX, Y_SC  + h_sc/2,  AC, ALW)
    darrow(ax, DX, Y_SC  - h_sc/2,    DX, Y_SOU + H_STD/2, AC, ALW)
    darrow(ax, DX, Y_SOU - H_STD/2,   DX, Y_ASS + H_STD/2, AC, ALW)
    darrow(ax, DX, Y_ASS - H_STD/2,   DX, Y_INC + H_STD/2, AC, ALW)

    # Other Methods: skip screening, go straight from ID to Sought
    darrow(ax, OX, Y_ID  - H_STD/2, OX, Y_SOU + H_STD/2, AC, ALW)
    darrow(ax, OX, Y_SOU - H_STD/2, OX, Y_ASS + H_STD/2, AC, ALW)
    darrow(ax, OX, Y_ASS - H_STD/2, OX, Y_INC + H_STD/2, AC, ALW)

    # All three streams → Total Included
    # Previous (left): L-shape — down then right
    my_prv = Y_INC - H_STD/2
    hline(ax, PX, TX - TW/2, my_prv, AC, ALW)
    darrow(ax, TX - TW/2, my_prv, TX, Y_TOT + H_STD/2, AC, ALW)

    # DB (centre): straight down
    darrow(ax, DX, Y_INC - H_STD/2, DX, Y_TOT + H_STD/2, AC, ALW)
    # Horizontal connector from DX to TX at the side of Total box
    hline(ax, DX, TX - TW/2 + (DX - (TX - TW/2)), Y_TOT + H_STD/2, AC, ALW)

    # Other (right): L-shape — down then left
    my_oth = Y_INC - H_STD/2
    hline(ax, OX, TX + TW/2, my_oth, AC, ALW)
    darrow(ax, TX + TW/2, my_oth, TX, Y_TOT + H_STD/2, AC, ALW)

    # Total → Analysis branches
    darrow(ax, TX, Y_TOT - H_STD/2, AX1, Y_AN + H_STD/2, AC, ALW)
    darrow(ax, TX, Y_TOT - H_STD/2, AX2, Y_AN + H_STD/2, AC, ALW)

    # ── Side-box branch connectors ─────────────────────────────────────────────
    # For each DB main-flow step, draw: right edge of main box → side exclusion box
    DB_LE  = DX + DW/2     # right edge of DB boxes
    DEX_LE = DEX - DEW/2   # left edge of DB side boxes
    OX_LE  = OX + OW/2     # right edge of Other boxes
    OEX_LE = OEX - OEW/2   # left edge of Other side boxes

    def branch_right(main_x, mx_right, side_x, sx_left, main_cy, side_cy):
        """Horizontal elbow from right edge of main box to side box."""
        mid_x = (mx_right + sx_left) / 2
        hline(ax, mx_right, mid_x, main_cy, AC, ALW)
        darrow(ax, mid_x, main_cy, sx_left, side_cy, AC, ALW)

    # DB identification → pre-screening removal
    branch_right(DX, DB_LE,  DEX, DEX_LE,
                 (Y_ID + Y_SC) / 2, Y_PRE)
    # DB screened → screened exclusions
    branch_right(DX, DB_LE,  DEX, DEX_LE,
                 (Y_SC + Y_SOU) / 2, Y_SCX)
    # DB sought → not retrieved
    branch_right(DX, DB_LE,  DEX, DEX_LE,
                 (Y_SOU + Y_ASS) / 2, Y_NR)
    # DB assessed → eligibility exclusions
    branch_right(DX, DB_LE,  DEX, DEX_LE,
                 (Y_ASS + Y_INC) / 2, Y_EX)

    # Other sought → not retrieved (if filled)
    if other_nr:
        branch_right(OX, OX_LE, OEX, OEX_LE,
                     (Y_SOU + Y_ASS) / 2, Y_NR)
    # Other assessed → eligibility exclusions (if filled)
    if other_exc_ft or d.get("other_exc_reason1", "").strip():
        branch_right(OX, OX_LE, OEX, OEX_LE,
                     (Y_ASS + Y_INC) / 2, Y_EX)

    # ── Phase band labels (academic / corporate / orange_flow) ────────────────
    if st.get("phase_bands"):
        ph_cols = st.get("phase_cols", ["#1a3a5c"] * 5)
        phases  = [
            ("IDENTIFICATION", Y_ID,  h_db_id),
            ("SCREENING",      Y_SC,  h_sc),
            ("RETRIEVAL",      Y_SOU, H_STD),
            ("ELIGIBILITY",    Y_ASS, H_STD),
            ("INCLUDED",       Y_TOT, H_STD),
        ]
        for (lbl, cy, ph), col in zip(phases, ph_cols):
            # Wider rounded pill with subtle glow shadow
            pill_sh = FancyBboxPatch(
                (0.09, cy - ph/2 - 0.06), 0.70, ph + 0.12,
                boxstyle="round,pad=0.05",
                facecolor="#000000", edgecolor="none", alpha=0.12, zorder=4)
            ax.add_patch(pill_sh)
            pill = FancyBboxPatch(
                (0.08, cy - ph/2 - 0.05), 0.68, ph + 0.10,
                boxstyle="round,pad=0.05",
                facecolor=col, edgecolor="none", alpha=0.94, zorder=5)
            ax.add_patch(pill)
            ax.text(0.42, cy, lbl, ha="center", va="center",
                    fontsize=UFS * 0.37, fontweight="bold", color="white",
                    rotation=90, zorder=6)

    # ── Title ──────────────────────────────────────────────────────────────────
    # Decorative title with flanking accent lines
    title_y = 21.68
    for lx1, lx2 in [(0.8, 7.0), (15.0, 21.2)]:
        ax.plot([lx1, lx2], [title_y, title_y],
                color=st["title_col"], lw=2.0, alpha=0.50, zorder=5)
    ax.text(11.0, title_y, "PRISMA 2020 Flow Diagram",
            ha="center", va="center", fontsize=16 * FS, fontweight="bold",
            color=st["title_col"])

    fig.tight_layout(pad=0.5)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor=bg)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# Auth routes
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")

        if not username or not email or not password:
            error = "All fields are required."
        elif len(username) < 3:
            error = "Username must be at least 3 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, generate_password_hash(password))
                )
                db.commit()
                user = db.execute("SELECT * FROM users WHERE username = ?",
                                  (username,)).fetchone()
                session["user_id"]  = user["id"]
                session["username"] = user["username"]
                db.close()
                return redirect(url_for("index"))
            except sqlite3.IntegrityError as e:
                db.close()
                error = ("Username already taken."
                         if "username" in str(e) else "Email already registered.")
    return render_template("signup.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db   = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?",
                          (username,)).fetchone()
        db.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))
        error = "Invalid username or password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ──────────────────────────────────────────────────────────────────────────────
# Main app routes  (all protected by @login_required)
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
@login_required
def index():
    return render_template("index.html")


@app.route("/use-style-img/<path:filename>")
@login_required
def use_style_img(filename):
    """Map the selected image's source to its assigned structural style."""
    sources = _collect_style_sources()
    for i, src in enumerate(sources):
        for img in src["images"]:
            if img.replace("\\", "/") == filename:
                key = SOURCE_TO_STYLE.get(src["label"], STYLE_KEYS[i % len(STYLE_KEYS)])
                return redirect(f"/?style={key}")
    return redirect("/")


@app.route("/clear-style")
@login_required
def clear_style():
    return redirect("/")


@app.route("/generate", methods=["POST"])
@login_required
def generate():
    d = request.form.to_dict()
    img_b64 = generate_diagram(d)

    # Auto-save to this user's diagram history
    title = "PRISMA Diagram \u2014 " + datetime.now().strftime("%b %d, %Y %H:%M")
    db  = get_db()
    cur = db.execute(
        "INSERT INTO diagrams (user_id, title, img_b64, form_data) VALUES (?, ?, ?, ?)",
        (session["user_id"], title, img_b64, json.dumps(d))
    )
    new_id = cur.lastrowid
    db.commit()
    db.close()

    return render_template("result.html", img=img_b64, data=d,
                           saved_title=title, diagram_id=new_id)


@app.route("/edit", methods=["POST"])
@login_required
def edit():
    d = request.form.to_dict()
    d.pop("format", None)
    return render_template("index.html", prefill=d)


# ── My Diagrams ───────────────────────────────────────────────────────────────

@app.route("/my-diagrams")
@login_required
def my_diagrams():
    db   = get_db()
    rows = db.execute(
        "SELECT id, title, created_at FROM diagrams "
        "WHERE user_id = ? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()
    db.close()
    return render_template("my_diagrams.html", diagrams=rows)


@app.route("/my-diagrams/<int:diagram_id>")
@login_required
def view_diagram(diagram_id):
    db  = get_db()
    row = db.execute(
        "SELECT * FROM diagrams WHERE id = ? AND user_id = ?",
        (diagram_id, session["user_id"])
    ).fetchone()
    db.close()
    if not row:
        return redirect(url_for("my_diagrams"))
    data = json.loads(row["form_data"])
    return render_template("result.html", img=row["img_b64"], data=data,
                           diagram_id=diagram_id, diagram_title=row["title"])


@app.route("/my-diagrams/<int:diagram_id>/img")
@login_required
def diagram_thumb(diagram_id):
    db  = get_db()
    row = db.execute(
        "SELECT img_b64 FROM diagrams WHERE id = ? AND user_id = ?",
        (diagram_id, session["user_id"])
    ).fetchone()
    db.close()
    if not row:
        return "", 404
    return send_file(io.BytesIO(base64.b64decode(row["img_b64"])), mimetype="image/png")


@app.route("/delete-diagram/<int:diagram_id>", methods=["POST"])
@login_required
def delete_diagram(diagram_id):
    db = get_db()
    db.execute(
        "DELETE FROM diagrams WHERE id = ? AND user_id = ?",
        (diagram_id, session["user_id"])
    )
    db.commit()
    db.close()
    return redirect(url_for("my_diagrams"))


# ── Design Gallery (development screenshots) ──────────────────────────────────

@app.route("/gallery")
@login_required
def gallery():
    paths = sorted(glob.glob(os.path.join(IMAGES_DIR, "*.png")) +
                   glob.glob(os.path.join(IMAGES_DIR, "*.jpg")) +
                   glob.glob(os.path.join(IMAGES_DIR, "*.jpeg")))
    filenames = [os.path.basename(p) for p in paths]
    return render_template("gallery.html", images=filenames, total=len(filenames))


@app.route("/gallery-img/<path:filename>")
@login_required
def gallery_img(filename):
    return send_from_directory(IMAGES_DIR, filename)


@app.route("/build-pdf")
@login_required
def build_pdf():
    _setup_matplotlib()   # ensure matplotlib is imported before use
    paths = sorted(glob.glob(os.path.join(IMAGES_DIR, "*.png")) +
                   glob.glob(os.path.join(IMAGES_DIR, "*.jpg")) +
                   glob.glob(os.path.join(IMAGES_DIR, "*.jpeg")))
    if not paths:
        return "No images found.", 404

    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis("off")
        ax.text(0.5, 0.6,  "Systematic Review",
                ha="center", va="center", fontsize=28, fontweight="bold",
                color="#1a3a5c", transform=ax.transAxes)
        ax.text(0.5, 0.50, "Design Strategy \u2014 Screenshot Report",
                ha="center", va="center", fontsize=16,
                color="#5a7fa0", transform=ax.transAxes)
        ax.text(0.5, 0.42, f"{len(paths)} screenshots captured during development",
                ha="center", va="center", fontsize=11,
                color="#888", transform=ax.transAxes)
        ax.text(0.5, 0.10, "PRISMA 2020 Flow Diagram Generator",
                ha="center", va="center", fontsize=9,
                color="#aaa", style="italic", transform=ax.transAxes)
        fig.patch.set_facecolor("white")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        for i, path in enumerate(paths, 1):
            img  = plt.imread(path)
            h, w = img.shape[:2]
            fig_w = 10.0
            fig_h = min(fig_w * h / w, 13.0)
            fig, ax = plt.subplots(figsize=(fig_w, fig_h))
            ax.imshow(img)
            ax.axis("off")
            fname = os.path.basename(path)
            fig.text(0.5, 0.01, f"Screen {i}/{len(paths)} \u2014 {fname}",
                     ha="center", fontsize=7, color="#aaa", style="italic")
            fig.patch.set_facecolor("white")
            fig.tight_layout(pad=0.3)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    buf.seek(0)
    return send_file(buf, mimetype="application/pdf",
                     download_name="systematic_review_design_report.pdf",
                     as_attachment=True)


# ── Download diagram ──────────────────────────────────────────────────────────

@app.route("/download", methods=["POST"])
@login_required
def download():
    d   = request.form.to_dict()
    fmt = d.pop("format", "png")
    fig = _build_fig(d)
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    mime = "application/pdf" if fmt == "pdf" else "image/png"
    return send_file(buf, mimetype=mime,
                     download_name=f"prisma_diagram.{fmt}", as_attachment=True)


def _build_fig(d):
    b64     = generate_diagram(d)
    data    = base64.b64decode(b64)
    img_buf = io.BytesIO(data)
    fig, ax = plt.subplots(figsize=(12, 14))
    img = plt.imread(img_buf)
    ax.imshow(img)
    ax.axis("off")
    fig.tight_layout(pad=0)
    return fig


# ── Different Styles gallery ──────────────────────────────────────────────────

def _collect_style_sources():
    exts    = ("*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG")
    sources = {}
    for entry in sorted(os.listdir(DIFF_STYLE_DIR)):
        full = os.path.join(DIFF_STYLE_DIR, entry)
        if os.path.isdir(full):
            imgs = []
            for ext in exts:
                imgs += glob.glob(os.path.join(full, ext))
            imgs = sorted(imgs)
            if imgs:
                sources[entry] = [os.path.join(entry, os.path.basename(p))
                                   for p in imgs]
        elif os.path.isfile(full) and any(
                full.lower().endswith(e) for e in [".png", ".jpg", ".jpeg"]):
            sources[entry] = [entry]
    result = []
    for label in sorted(sources.keys(), key=lambda x: x.lower()):
        result.append({
            "label":  label.replace(".png","").replace(".jpg","").replace(".jpeg",""),
            "images": sources[label]
        })
    return result


def _collect_generated_previews():
    """Return a list of dicts for every generated style preview."""
    previews = []
    for idx, key in enumerate(STYLE_KEYS, 1):
        st     = DIAGRAM_STYLES[key]
        folder = os.path.join(GEN_STYLE_DIR, f"{idx:02d}_{key}")
        if not os.path.isdir(folder):
            continue
        pngs = sorted(glob.glob(os.path.join(folder, "*.png")))
        if not pngs:
            continue
        fname = os.path.basename(pngs[0])
        previews.append({
            "key":   key,
            "name":  st["name"],
            "color": st.get("inc_edge", st.get("box_edge", "#27ae60")),
            "img":   f"{idx:02d}_{key}/{fname}",
        })
    return previews


@app.route("/styles")
@login_required
def styles():
    sources = _collect_style_sources()
    total   = sum(len(s["images"]) for s in sources)
    for i, src in enumerate(sources):
        key = SOURCE_TO_STYLE.get(src["label"], STYLE_KEYS[i % len(STYLE_KEYS)])
        src["theme"]       = key
        src["theme_name"]  = DIAGRAM_STYLES[key]["name"]
        src["theme_color"] = DIAGRAM_STYLES[key]["inc_edge"]
    previews = _collect_generated_previews()
    return render_template("styles.html", sources=sources, total=total,
                           nsources=len(sources), themes=DIAGRAM_STYLES,
                           previews=previews)


@app.route("/styles-img/<path:filename>")
@login_required
def styles_img(filename):
    directory = DIFF_STYLE_DIR
    parts     = filename.split("/", 1)
    if len(parts) == 2:
        directory = os.path.join(DIFF_STYLE_DIR, parts[0])
        filename  = parts[1]
    return send_from_directory(directory, filename)


@app.route("/gen-style-img/<path:filename>")
@login_required
def gen_style_img(filename):
    """Serve generated style preview images."""
    directory = GEN_STYLE_DIR
    parts     = filename.split("/", 1)
    if len(parts) == 2:
        directory = os.path.join(GEN_STYLE_DIR, parts[0])
        filename  = parts[1]
    return send_from_directory(directory, filename)


# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
