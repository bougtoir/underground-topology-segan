"""CEUS figure prep: TIFF versions + methodology pipeline figure.
All raster figures already exist as PNG; convert to TIFF and draw a
programmatic data-to-decision pipeline schematic."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = f"{ROOT}/figures"

for f in ["v4_fig1_study_zones", "v4_fig2_topology_example", "v4_fig3_delta",
          "v4_fig4_tornado", "v4_supp_figS1_dg", "ceus_fig_morphology",
          "ceus_fig_decomposition"]:
    src = f"{FIG}/{f}.png"
    dst = f"{FIG}/{f}.tiff"
    if os.path.exists(src):
        Image.open(src).save(dst, compression="tiff_lzw")

# pipeline schematic
fig, ax = plt.subplots(figsize=(7.2, 3.0))
ax.axis("off")
boxes = [
    (0.02, "Open data inputs", "roads & buildings (OSM)\nsecurity-light anchors\nengineering datasheets"),
    (0.27, "Zone construction", "largest connected component\ndemand snapping\nMV-exclusion (>150 kW)"),
    (0.52, "Reconstruction", "legacy LV ensemble\n(data tiers 1–3)\nfeasibility gates"),
    (0.77, "Decision model", "incumbent admissible\nVoF estimand\nlife-cycle cost"),
]
for x0, title, sub in boxes:
    ax.add_patch(FancyBboxPatch((x0, 0.30), 0.20, 0.46,
                 boxstyle="round,pad=0.012", fc="#eef3fb", ec="#335", lw=1.1))
    ax.text(x0 + 0.10, 0.66, title, ha="center", fontsize=10,
            fontweight="bold", color="#223")
    ax.text(x0 + 0.10, 0.47, sub, ha="center", va="center", fontsize=7.6, color="#334")
for x0 in [0.22, 0.47, 0.72]:
    ax.add_patch(FancyArrowPatch((x0 + 0.005, 0.53), (x0 + 0.045, 0.53),
                 arrowstyle="-|>", mutation_scale=14, lw=1.4, color="#335"))
ax.text(0.5, 0.10, "planning-support output: feasibility-adjusted value of "
        "topology flexibility at renewal (screening, not engineering design)",
        ha="center", fontsize=8.4, style="italic", color="#334")
fig.tight_layout()
for ext in ["png", "tiff"]:
    fig.savefig(f"{FIG}/ceus_fig_pipeline.{ext}", dpi=300, bbox_inches="tight")
print("done")
