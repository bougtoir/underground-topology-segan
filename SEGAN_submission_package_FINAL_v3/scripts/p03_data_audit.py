"""Phase 3: audit downloaded municipal data -> analysis/data_audit.csv"""
import pandas as pd, glob, hashlib, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data/raw")
OUT = os.path.join(ROOT, "analysis/data_audit.csv")

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

rows = []

# --- Sano (cp932) ---
p = f"{RAW}/sano/sano_security_lights.csv"
s = pd.read_csv(p, encoding="cp932")
rows.append(dict(municipality="Sano", file="sano_security_lights.csv",
                 rows=len(s), cols=len(s.columns), encoding="cp932",
                 lat_null=int(s["緯度"].isna().sum()), lon_null=int(s["経度"].isna().sum()),
                 pole_field="電柱番号", pole_dupes=int(s["電柱番号"].duplicated().sum()),
                 lat_min=float(s["緯度"].min()), lat_max=float(s["緯度"].max()),
                 lon_min=float(s["経度"].min()), lon_max=float(s["経度"].max()),
                 sha256=sha256(p), tier=1))
s.to_csv(f"{ROOT}/data/processed/sano_anchors.csv", index=False)

# --- Kudamatsu (cp932, 3 files) ---
frames = []
for f in sorted(glob.glob(f"{RAW}/kudamatsu/*.csv")):
    frames.append(pd.read_csv(f, encoding="cp932"))
k = pd.concat(frames, ignore_index=True)
rows.append(dict(municipality="Kudamatsu", file="352071_security_lights*.csv (3 parts)",
                 rows=len(k), cols=len(k.columns), encoding="cp932",
                 lat_null=int(k["緯度"].isna().sum()), lon_null=int(k["経度"].isna().sum()),
                 pole_field="防犯灯_ID (security-light id, NOT pole no)",
                 pole_dupes=int(k["防犯灯_ID"].duplicated().sum()),
                 lat_min=float(k["緯度"].min()), lat_max=float(k["緯度"].max()),
                 lon_min=float(k["経度"].min()), lon_max=float(k["経度"].max()),
                 sha256=";".join(sha256(f) for f in sorted(glob.glob(f"{RAW}/kudamatsu/*.csv"))),
                 tier=2))
k[["緯度","経度","防犯灯_ID"]].to_csv(f"{ROOT}/data/processed/kudamatsu_anchors.csv", index=False)

rows.append(dict(municipality="Yasu", file="(none downloaded)", rows=0, cols=0,
                 encoding="-", lat_null=-1, lon_null=-1, pole_field="-",
                 pole_dupes=-1, lat_min=float("nan"), lat_max=float("nan"),
                 lon_min=float("nan"), lon_max=float("nan"), sha256="-", tier=3))

pd.DataFrame(rows).to_csv(OUT, index=False)
print(pd.DataFrame(rows)[["municipality","rows","pole_field","tier"]].to_string(index=False))
print("wrote", OUT)
