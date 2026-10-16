"""Phase CEUS-GC: Figure 2 rebuild — panel (a) Japan location inset +
(b)-(d) existing study-zone road/demand maps. Data: geoBoundaries JPN ADM1
(CC-BY-4.0, wmgeolab), zone.geojson centroids mark analysis zones."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import geopandas as gpd
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = f"{ROOT}/figures"
plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans",
                     "figure.dpi": 300, "savefig.dpi": 300})
CITIES = ["sano", "kudamatsu", "yasu"]
CNAMES = {"sano": "Sano (Tochigi)", "kudamatsu": "Kudamatsu (Yamaguchi)",
          "yasu": "Yasu (Shiga)"}

jp = gpd.read_file(f"{ROOT}/data/raw/geoboundaries/geoBoundaries-JPN-ADM1.geojson")
# Northern-island coastlines from Natural Earth 10m land (public domain):
# individual island polygons NE of Hokkaido (Habomai, Shikotan, Kunashir,
# Etorofu, Urup and adjacent islets). Selection is by island-polygon
# centroid only — a visual-scope data filter, not a sovereignty statement;
# no opposing mainland coastline is drawn.
from shapely.geometry import box as _box
_ne = gpd.read_file(f"{ROOT}/data/raw/naturalearth/ne_10m_land/ne_10m_land.shp")
_polys = []
for _g in _ne.geometry:
    _polys += list(_g.geoms) if _g.geom_type == "MultiPolygon" else [_g]
_win = _box(143.4, 43.0, 150.5, 46.4)
kuril = gpd.GeoSeries(
    [p for p in _polys if _win.contains(p.centroid) and p.area < 3],
    crs=_ne.crs)

fig = plt.figure(figsize=(7.0, 3.1))
axj = fig.add_axes([0.005, 0.06, 0.265, 0.88])
jp.plot(ax=axj, color="#f2f2f2", edgecolor="0.55", lw=0.35)
kuril.plot(ax=axj, color="#f2f2f2", edgecolor="0.55", lw=0.35)
mk = {"sano": (139.5777, 36.3274), "kudamatsu": (131.8733, 34.0244),
      "yasu": (136.0294, 35.0727)}
style = {"sano": ("o", "#0072B2"), "kudamatsu": ("s", "#E69F00"),
         "yasu": ("^", "#009E73")}
for z, (lon, lat) in mk.items():
    m, c = style[z]
    axj.plot(lon, lat, marker=m, ms=5, mfc=c, mec="k", mew=0.5, zorder=5)
axj.set_xlim(122.0, 150.5); axj.set_ylim(23.5, 46.5)
axj.set_xticks([]); axj.set_yticks([])
axj.set_aspect(1/np.cos(np.deg2rad(36)))
axj.set_title("(a) Japan", fontsize=8, loc="left")

handles = [plt.Line2D([], [], marker=style[z][0], color="none", mfc=style[z][1],
                      mec="k", mew=0.5, ms=5, label=CNAMES[z].split(" (")[0])
           for z in CITIES]
axj.legend(handles=handles, loc="upper left", fontsize=6.5, frameon=True,
           framealpha=1.0, edgecolor="0.4", borderpad=0.45, labelspacing=0.35,
           handletextpad=0.5)

for i, name in enumerate(CITIES):
    ax = fig.add_axes([0.30 + 0.235 * i, 0.06, 0.225, 0.88])
    e = pd.read_csv(f"{ROOT}/data/processed/{name}/edges.csv")
    n = pd.read_csv(f"{ROOT}/data/processed/{name}/nodes.csv").set_index("node")
    for _, r in e.iterrows():
        try:
            u, v = n.loc[r["u"]], n.loc[r["v"]]
            ax.plot([u.lon, v.lon], [u.lat, v.lat], lw=0.3, c="0.7")
        except KeyError:
            continue
    dn = n[n["p_kw"] > 0]
    ax.scatter(dn.lon, dn.lat, s=2, c="tab:blue", zorder=3)
    ax.set_title(f"({'bcd'[i]}) {CNAMES[name].split(' ')[0]}",
                 fontsize=8, loc="left")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_aspect(1/np.cos(np.deg2rad(36)))

fig.savefig(f"{FIG}/v4_fig1_study_zones.png", bbox_inches="tight")
fig.savefig(f"{FIG}/v4_fig1_study_zones.pdf", bbox_inches="tight")
Image.open(f"{FIG}/v4_fig1_study_zones.png").save(
    f"{FIG}/v4_fig1_study_zones.tiff", compression="tiff_lzw")
plt.close(fig)
print("saved figures/v4_fig1_study_zones.{png,tiff,pdf}")
