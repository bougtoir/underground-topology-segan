"""Inventory every persisted raw input with checksum and acquisition metadata."""
import hashlib
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = f"{ROOT}/data/raw"

SOURCES = {
    "sano/sano_security_lights.csv": (
        "Sano City security-light inventory", "SANO-SEC-001",
        "https://www.city.sano.lg.jp/material/files/group/17/100.csv",
        "single municipal CSV snapshot", "Sano City open-data terms"),
    "kudamatsu/352071_security_lights1-2000.csv": (
        "Kudamatsu security-light inventory rows 1-2000", "KUDA-SEC-001",
        "https://yamaguchi-opendata.jp/ckan/dataset/cbc4f005-7812-41f6-8f5a-b9ed044a4f81/resource/91ad1a3d-3790-4bb0-8f60-1d8f061ba9c4/download/352071_security_lights1-2000.csv",
        "CKAN resource; first published partition", "CC BY"),
    "kudamatsu/352071_security_lights2001-4000.csv": (
        "Kudamatsu security-light inventory rows 2001-4000", "KUDA-SEC-002",
        "https://yamaguchi-opendata.jp/ckan/dataset/cbc4f005-7812-41f6-8f5a-b9ed044a4f81/resource/b58e497f-3db1-4bfc-ac6b-4de6bdfdd874/download/352071_security_lights2001-4000.csv",
        "CKAN resource; second published partition", "CC BY"),
    "kudamatsu/352071_security_lights4001.csv": (
        "Kudamatsu security-light inventory rows 4001 onward", "KUDA-SEC-003",
        "https://yamaguchi-opendata.jp/ckan/dataset/cbc4f005-7812-41f6-8f5a-b9ed044a4f81/resource/d94036a3-3071-415c-bfa9-e44d9377eac3/download/352071_security_lights4001.csv",
        "CKAN resource; final published partition", "CC BY"),
    "engineering_sources/fujikura_6600V_CV_EE_CVT_EE.pdf": (
        "Fujikura-Dia 6600 V CV/CVT cable catalogue", "ENG-CABLE-001",
        "https://www.fujikura-dia.co.jp/pdf/catalog/catalog-6600V_CV-EE-CVT-EE.pdf",
        "public manufacturer PDF snapshot", "copyright retained by publisher"),
    "engineering_sources/toshiba_2026_transformer_catalog.pdf": (
        "Toshiba 2026 top-runner oil transformer catalogue", "ENG-TR-001",
        "https://www.toshiba-tips.co.jp/products/assets/pdf/catalog/trs/CKTB-4000_Sseries_Web_20251024.pdf",
        "public manufacturer PDF snapshot", "copyright retained by publisher"),
    "engineering_sources/chuki_6kV_pole_transformer.pdf": (
        "Chuki 6 kV pole-transformer catalogue", "ENG-TR-002",
        "https://www.chuki.jp/wp-content/uploads/2024/03/catalog08_01.pdf",
        "public manufacturer PDF snapshot", "copyright retained by publisher"),
    "engineering_sources/kitaniti_6600V_CVT_impedance_60Hz.html": (
        "Kitanihon 6600 V CVT 60 Hz impedance table", "ENG-CABLE-002",
        "https://www.kitaniti-td.co.jp/technical/08/04_08/index08_04_08.html",
        "complete HTML response snapshot", "website terms; copyright retained"),
    "engineering_sources/pandapower_CIGRE_network_docs.html": (
        "pandapower CIGRE network documentation", "BENCH-CIGRE-001",
        "https://pandapower.readthedocs.io/en/latest/networks/cigre.html",
        "complete HTML response snapshot", "pandapower documentation licence"),
    "engineering_sources/egov_electricity_business_act_enforcement_regulations.xml": (
        "Electricity Business Act Enforcement Regulations XML", "LAW-001-XML",
        "https://laws.e-gov.go.jp/api/1/lawdata/407M50000400077",
        "e-Gov law API response", "Japanese Laws Translation/open government data"),
    "engineering_sources/egov_electricity_business_act_enforcement_regulations_20241101.html": (
        "Electricity Business Act Enforcement Regulations HTML", "LAW-001-HTML",
        "https://laws.e-gov.go.jp/law/407M50000400077/20241101_506M60000400073",
        "versioned e-Gov HTML response", "Japanese Laws Translation/open government data"),
}


def metadata(relative_path):
    if relative_path in SOURCES:
        return SOURCES[relative_path]
    if relative_path.startswith("osm_cache/"):
        return (
            "OSMnx cached Overpass response", f"OSM-CACHE-{relative_path[10:18]}",
            "https://overpass-api.de/api/interpreter",
            "complete response cache for one OSMnx query; completeness is "
            "subject to the Overpass service response at retrieval", "ODbL")
    if relative_path.startswith("osm_"):
        city = relative_path.split("_")[1].split(".")[0]
        kind = "building footprints" if "_buildings." in relative_path else "road graph"
        return (
            f"OpenStreetMap {kind} snapshot for {city}", f"OSM-{city.upper()}-{kind[:4].upper()}",
            "https://overpass-api.de/api/interpreter",
            "OSMnx municipality query saved as a persistent snapshot", "ODbL")
    raise ValueError(f"Missing acquisition metadata for raw input: {relative_path}")


rows = []
for directory, _, filenames in os.walk(RAW):
    for filename in sorted(filenames):
        path = os.path.join(directory, filename)
        relative_path = os.path.relpath(path, RAW)
        description, identifier, url, conditions, terms = metadata(relative_path)
        with open(path, "rb") as stream:
            digest = hashlib.sha256(stream.read()).hexdigest()
        rows.append({
            "source_id": identifier,
            "description": description,
            "source_url": url,
            "data_identifier_or_version": identifier,
            "retrieval_date_utc": "2026-09-24",
            "retrieval_time_precision": "date; exact time unavailable",
            "retrieval_conditions": conditions,
            "local_path": f"data/raw/{relative_path}",
            "size_bytes": os.path.getsize(path),
            "sha256": digest,
            "license_or_terms": terms,
            "snapshot_status": "persisted and checksum-verified",
        })

registry = pd.DataFrame(rows).sort_values("local_path")
registry.to_csv(f"{ROOT}/provenance/source_registry.csv", index=False)
registry.to_csv(f"{ROOT}/RAW_DATA_ACQUISITION_REGISTRY.csv", index=False)
print(f"registered {len(registry)} persisted raw inputs")
