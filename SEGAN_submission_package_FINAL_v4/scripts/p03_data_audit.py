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
pole = s["電柱番号"]
nonmissing_pole = pole.dropna()
pole_counts = nonmissing_pole.value_counts()
rows.append(dict(municipality="Sano", file="sano_security_lights.csv",
                 rows=len(s), cols=len(s.columns), encoding="cp932",
                 lat_null=int(s["緯度"].isna().sum()), lon_null=int(s["経度"].isna().sum()),
                 pole_field="電柱番号", pole_dupes=int(len(nonmissing_pole) - nonmissing_pole.nunique()),
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

registry = pd.read_csv(f"{ROOT}/provenance/source_registry.csv")
municipal_rows = [
    dict(
        municipality="Sano", dataset="municipal security-light inventory",
        source_ids="SANO-SEC-001",
        source_url=registry.loc[registry.source_id == "SANO-SEC-001", "source_url"].iloc[0],
        retrieval_date_utc="2026-09-24",
        license_or_terms="Sano City open-data terms; secondary use stated as permitted",
        raw_files="data/raw/sano/sano_security_lights.csv",
        rows=len(s), coordinate_nulls=int(s[["緯度", "経度"]].isna().any(axis=1).sum()),
        coordinate_semantics="coordinates of security-light inventory records; not verified pole coordinates",
        identifier_field="電柱番号 (utility-pole-number field)",
        identifier_missing=int(pole.isna().sum()),
        identifier_unique=int(nonmissing_pole.nunique()),
        duplicate_extra_records=int(len(nonmissing_pole) - nonmissing_pole.nunique()),
        multi_record_identifier_groups=int((pole_counts > 1).sum()),
        maximum_records_per_identifier=int(pole_counts.max()),
        exact_coordinate_duplicate_rows=int(s.duplicated(["緯度", "経度"], keep=False).sum()),
        evidence_tier="pole-ID-linked light inventory",
        defensible_use="location anchors and pole-ID linkage only",
        prohibited_inference="coordinates are observed pole locations or records exhaust the utility network",
        audit_status="usable_with_semantic_caveat"),
    dict(
        municipality="Kudamatsu", dataset="municipal security-light inventory",
        source_ids="KUDA-SEC-001;KUDA-SEC-002;KUDA-SEC-003",
        source_url="https://yamaguchi-opendata.jp/ckan/dataset/cbc4f005-7812-41f6-8f5a-b9ed044a4f81",
        retrieval_date_utc="2026-09-24", license_or_terms="CC-BY",
        raw_files="data/raw/kudamatsu/352071_security_lights*.csv",
        rows=len(k), coordinate_nulls=int(k[["緯度", "経度"]].isna().any(axis=1).sum()),
        coordinate_semantics="coordinates of security-light records in a world geodetic reference system",
        identifier_field="防犯灯_ID (security-light ID; not a pole ID)",
        identifier_missing=int(k["防犯灯_ID"].isna().sum()),
        identifier_unique=int(k["防犯灯_ID"].nunique()),
        duplicate_extra_records=int(len(k) - k["防犯灯_ID"].nunique()),
        multi_record_identifier_groups=int((k["防犯灯_ID"].value_counts() > 1).sum()),
        maximum_records_per_identifier=int(k["防犯灯_ID"].value_counts().max()),
        exact_coordinate_duplicate_rows=int(k.duplicated(["緯度", "経度"], keep=False).sum()),
        evidence_tier="geolocated light anchors without pole linkage",
        defensible_use="location anchors only",
        prohibited_inference="security-light IDs identify utility poles or reveal feeder connectivity",
        audit_status="usable_as_location_anchors"),
    dict(
        municipality="Yasu", dataset="OpenStreetMap roads and buildings",
        source_ids="OSM-YASU-ROAD;OSM-YASU-BUIL",
        source_url="https://www.openstreetmap.org/",
        retrieval_date_utc="2026-09-24", license_or_terms="ODbL",
        raw_files="data/raw/osm_yasu.graphml;data/raw/osm_yasu_buildings.geojson",
        rows=0, coordinate_nulls="", coordinate_semantics="OSM geometries",
        identifier_field="", identifier_missing="", identifier_unique="",
        duplicate_extra_records="", multi_record_identifier_groups="",
        maximum_records_per_identifier="", exact_coordinate_duplicate_rows="",
        evidence_tier="roads/buildings only",
        defensible_use="road-corridor and modeled building-demand geography",
        prohibited_inference="observed poles, conductors, transformers or feeder connectivity",
        audit_status="usable_for_reconstructed_scenario_only"),
]
pd.DataFrame(municipal_rows).to_csv(
    f"{ROOT}/MUNICIPAL_DATA_PROVENANCE_AUDIT.csv", index=False)
print(pd.DataFrame(rows)[["municipality","rows","pole_field","tier"]].to_string(index=False))
print("wrote", OUT)
