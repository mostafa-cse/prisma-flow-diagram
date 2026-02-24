#!/usr/bin/env python3
"""
Generate a PRISMA 2020 Flow Diagram PNG for every DIAGRAM_STYLE.

Creates:
  Generated Styles/
    01_classic/PRISMA_Classic_Blue.png
    02_academic/PRISMA_Academic_Square.png
    ...
    11_teal/PRISMA_Ocean_Teal.png

Also creates a combined overview image (all 11 thumbnails on one page).
"""

import io, os, sys, base64

# ── import the app module so we can reuse DIAGRAM_STYLES + generate_diagram ──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import DIAGRAM_STYLES, STYLE_KEYS, generate_diagram

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "Generated Styles")

# ── Sample data that fills every field nicely ─────────────────────────────────
SAMPLE_DATA = {
    "total_identified": "1250",
    "db1_name": "PubMed",       "db1_count": "520",
    "db2_name": "Scopus",       "db2_count": "380",
    "db3_name": "Web of Science","db3_count": "250",
    "db4_name": "IEEE Xplore",  "db4_count": "100",
    "db5_name": "",             "db5_count": "",
    "db6_name": "",             "db6_count": "",
    "screened":      "980",
    "sc_included":   "620",
    "sc_excluded":   "310",
    "conflict_total":"50",
    "conflict_inc":  "30",
    "conflict_exc":  "20",
    "duplicates":    "270",
    "exc_screened":  "330",
    "retrieval":     "650",
    "not_retrieved":  "45",
    "eligibility":   "605",
    "exc_fulltext":  "280",
    "exc_reason1":   "Wrong population",  "exc_reason1_n": "95",
    "exc_reason2":   "Wrong outcome",     "exc_reason2_n": "75",
    "exc_reason3":   "No full text",      "exc_reason3_n": "60",
    "exc_reason4":   "Duplicate data",    "exc_reason4_n": "30",
    "exc_reason5":   "Wrong study design","exc_reason5_n": "20",
    "included":      "325",
}


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    generated_paths = []

    for idx, key in enumerate(STYLE_KEYS, 1):
        style_info = DIAGRAM_STYLES[key]
        style_name = style_info["name"]
        safe_name  = style_name.replace(" ", "_").replace("&", "and")

        # Create subfolder  e.g.  01_classic/
        folder = os.path.join(OUTPUT_DIR, f"{idx:02d}_{key}")
        os.makedirs(folder, exist_ok=True)

        # Generate diagram
        d = dict(SAMPLE_DATA)
        d["style"] = key
        b64_png = generate_diagram(d)

        # Save PNG
        png_bytes = base64.b64decode(b64_png)
        filename  = f"PRISMA_{safe_name}.png"
        filepath  = os.path.join(folder, filename)
        with open(filepath, "wb") as f:
            f.write(png_bytes)

        generated_paths.append(filepath)
        print(f"  [{idx:2d}/11]  {key:12s}  →  {filepath}")

    # ── Build overview image (all 11 on one sheet) ────────────────────────────
    print("\nBuilding combined overview …")
    ncols, nrows = 4, 3
    fig, axes = plt.subplots(nrows, ncols, figsize=(28, 24))
    fig.patch.set_facecolor("white")
    fig.suptitle("PRISMA 2020 — All Diagram Styles", fontsize=22, fontweight="bold",
                 color="#1a3a5c", y=0.98)

    for i, ax in enumerate(axes.flat):
        if i < len(generated_paths):
            img = mpimg.imread(generated_paths[i])
            ax.imshow(img)
            key  = STYLE_KEYS[i]
            name = DIAGRAM_STYLES[key]["name"]
            ax.set_title(f"{i+1}. {name}", fontsize=11, fontweight="bold", pad=6)
        ax.axis("off")

    fig.tight_layout(rect=[0, 0, 1, 0.96], pad=1.5)
    overview_path = os.path.join(OUTPUT_DIR, "ALL_STYLES_OVERVIEW.png")
    fig.savefig(overview_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Overview  →  {overview_path}")

    print(f"\n✓ Done — {len(generated_paths)} diagrams + 1 overview saved to:\n  {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
