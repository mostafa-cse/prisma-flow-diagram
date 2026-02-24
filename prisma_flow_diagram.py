"""
PRISMA 2020 Flow Diagram
Recreated using matplotlib — Page et al. (2021)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


# ── helpers ──────────────────────────────────────────────────────────────────

def draw_box(ax, x, y, w, h, text, fontsize=8.5,
             facecolor="white", edgecolor="#2c3e50", linewidth=1.2,
             bold_first_line=False):
    """Draw a rounded rectangle with wrapped text."""
    box = FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.02",
        linewidth=linewidth,
        edgecolor=edgecolor,
        facecolor=facecolor,
        zorder=3,
    )
    ax.add_patch(box)

    lines = text.split("\n")
    if bold_first_line and lines:
        # first line bold, rest normal
        first = lines[0]
        rest  = "\n".join(lines[1:])
        ax.text(x, y + (h * 0.18 if rest else 0), first,
                ha="center", va="center", fontsize=fontsize,
                fontweight="bold", zorder=4, wrap=True,
                multialignment="left")
        if rest:
            ax.text(x, y - h * 0.18, rest,
                    ha="center", va="center", fontsize=fontsize - 0.5,
                    zorder=4, multialignment="left")
    else:
        ax.text(x, y, text,
                ha="center", va="center", fontsize=fontsize,
                zorder=4, multialignment="left")


def arrow(ax, x1, y1, x2, y2, color="#2c3e50"):
    """Draw a solid arrow between two points."""
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=1.3,
            mutation_scale=12,
        ),
        zorder=2,
    )


def hline(ax, x1, x2, y, color="#2c3e50"):
    """Draw a horizontal connector line (no arrowhead)."""
    ax.plot([x1, x2], [y, y], color=color, lw=1.3, zorder=2)


# ── canvas ───────────────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(11, 13))
ax.set_xlim(0, 10)
ax.set_ylim(0, 13.5)
ax.axis("off")

# ── layout constants ─────────────────────────────────────────────────────────

LEFT_X   = 3.5   # centre-x of main (left) column boxes
RIGHT_X  = 7.8   # centre-x of right-side exclusion boxes
BOX_W    = 5.6   # width  of main boxes
SIDE_W   = 3.6   # width  of side boxes
BH_MAIN  = 1.05  # height of main boxes
BH_SIDE  = 0.85  # height of side boxes (small)
BH_SIDE2 = 1.40  # height of taller side boxes

# Y positions of main boxes (top → bottom)
Y = {
    "identified" : 12.3,
    "screened"   : 9.3,
    "retrieval"  : 6.4,
    "eligibility": 3.8,
    "included"   : 1.2,
}

# ── MAIN BOXES ───────────────────────────────────────────────────────────────

# 1. Identified
draw_box(
    ax, LEFT_X, Y["identified"], BOX_W, 1.55,
    "Records identified from database searching (n = 356):\n"
    "  • Scopus: 200\n"
    "  • IEEE : 60\n"
    "  • Researchget: 46\n"
    "  • Google Scholar: 16\n"
    "  • Academia.edu: 5\n",
    "  • arXiv: 29\n",
    "  • CORE : 9",
    fontsize=8.2, bold_first_line=True,
)

# 2. Screened
draw_box(
    ax, LEFT_X, Y["screened"], BOX_W, 1.35,
    "Records screened (n = 258):\n"
    "  • Included: 29\n"
    "  • Excluded: 204\n"
    "  • Conflict: 25\n"
    "       ◦ Included: 5\n"
    "       ◦ Excluded: 20",
    fontsize=8.2, bold_first_line=True,
)

# 3. Sought for retrieval
draw_box(
    ax, LEFT_X, Y["retrieval"], BOX_W, BH_MAIN,
    "Records sought for retrieval (n = 34)",
    fontsize=9, bold_first_line=True,
)

# 4. Eligibility
draw_box(
    ax, LEFT_X, Y["eligibility"], BOX_W, BH_MAIN,
    "Records assessed for eligibility (n = 34)",
    fontsize=9, bold_first_line=True,
)

# 5. Included
draw_box(
    ax, LEFT_X, Y["included"], BOX_W, BH_MAIN,
    "Studies included in review (n = 25)",
    fontsize=9.5, bold_first_line=True,
    facecolor="#eaf4fb", edgecolor="#1a6fa0",
)

# ── SIDE BOXES ───────────────────────────────────────────────────────────────

# Side 1 — duplicates removed  (between identified and screened)
side1_y = (Y["identified"] + Y["screened"]) / 2
draw_box(
    ax, RIGHT_X, side1_y, SIDE_W, BH_SIDE,
    "Duplicate records removed\nbefore screening (n = 98)",
    fontsize=8.5,
)

# Side 2 — records excluded after screening
side2_y = (Y["screened"] + Y["retrieval"]) / 2
draw_box(
    ax, RIGHT_X, side2_y, SIDE_W, 1.10,
    "Records excluded (n = 224):\n"
    "  • Excluded at first (n = 204)\n"
    "  • Excluded after discussion (n = 20)",
    fontsize=8.2, bold_first_line=True,
)

# Side 3 — not retrieved
side3_y = (Y["retrieval"] + Y["eligibility"]) / 2
draw_box(
    ax, RIGHT_X, side3_y, SIDE_W, BH_SIDE,
    "Records not retrieved (n = 0)",
    fontsize=8.5,
)

# Side 4 — excluded at full-text
side4_y = (Y["eligibility"] + Y["included"]) / 2
draw_box(
    ax, RIGHT_X, side4_y, SIDE_W, 1.30,
    "Records excluded (n = 9):\n"
    "  • Non-school settings: 2\n"
    "  • No implementation: 3\n"
    "  • Different outcomes: 2\n"
    "  • Different population: 2",
    fontsize=8.2, bold_first_line=True,
)

# ── ARROWS — main column (vertical) ──────────────────────────────────────────

arrow(ax, LEFT_X, Y["identified"] - 0.78, LEFT_X, Y["screened"]   + 0.68)
arrow(ax, LEFT_X, Y["screened"]   - 0.68, LEFT_X, Y["retrieval"]  + 0.53)
arrow(ax, LEFT_X, Y["retrieval"]  - 0.53, LEFT_X, Y["eligibility"]+ 0.53)
arrow(ax, LEFT_X, Y["eligibility"]- 0.53, LEFT_X, Y["included"]   + 0.53)

# ── ARROWS — horizontal connectors to side boxes ─────────────────────────────

left_edge  = LEFT_X + BOX_W / 2          # right edge of main boxes
right_edge = RIGHT_X - SIDE_W / 2        # left edge of side boxes

def side_arrow(ax, main_y, side_y):
    """Horizontal line from main box mid-right → side box left edge."""
    mid_x   = (left_edge + right_edge) / 2
    hline(ax, left_edge, mid_x, main_y)
    arrow(ax, mid_x, main_y, right_edge, side_y)


# between identified → screened  (duplicate side box)
gap1_y = (Y["identified"] + Y["screened"]) / 2
hline(ax, left_edge, (left_edge + right_edge) / 2, gap1_y)
arrow(ax, (left_edge + right_edge) / 2, gap1_y, right_edge, side1_y)

# between screened → retrieval  (excluded side box)
gap2_y = (Y["screened"] + Y["retrieval"]) / 2
hline(ax, left_edge, (left_edge + right_edge) / 2, gap2_y)
arrow(ax, (left_edge + right_edge) / 2, gap2_y, right_edge, side2_y)

# between retrieval → eligibility  (not retrieved side box)
gap3_y = (Y["retrieval"] + Y["eligibility"]) / 2
hline(ax, left_edge, (left_edge + right_edge) / 2, gap3_y)
arrow(ax, (left_edge + right_edge) / 2, gap3_y, right_edge, side3_y)

# between eligibility → included  (excluded full-text side box)
gap4_y = (Y["eligibility"] + Y["included"]) / 2
hline(ax, left_edge, (left_edge + right_edge) / 2, gap4_y)
arrow(ax, (left_edge + right_edge) / 2, gap4_y, right_edge, side4_y)

# ── TITLE & CAPTION ──────────────────────────────────────────────────────────

ax.text(5, 13.2, "PRISMA 2020 Flow Diagram",
        ha="center", va="center", fontsize=13, fontweight="bold",
        color="#2c3e50")

ax.text(5, 0.35,
        "Fig. 1.  Flow diagram of data collection adopted from Page et al. (2021).",
        ha="center", va="center", fontsize=8.5,
        style="italic", color="#555555")

# ── SAVE ─────────────────────────────────────────────────────────────────────

fig.tight_layout()
fig.savefig("prisma_flow_diagram.png", dpi=200, bbox_inches="tight",
            facecolor="white")
fig.savefig("prisma_flow_diagram.pdf", bbox_inches="tight",
            facecolor="white")

print("Saved: prisma_flow_diagram.png  &  prisma_flow_diagram.pdf")
plt.show()
