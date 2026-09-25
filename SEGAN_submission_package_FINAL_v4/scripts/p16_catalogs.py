"""Phase 16 (forensic revision): build machine-readable cable and transformer
catalogues from the locally archived manufacturer primary sources.

Sources (archived under data/raw/engineering_sources/, checksums verified here):
  * fujikura_6600V_CV_EE_CVT_EE.pdf  -- Fujikura 6600 V CV/CVT construction and
    performance table: nominal area, conductor outer diameter, insulation
    thickness, core outer diameter, 20 degC conductor resistance and 40 degC
    air ampacity (1-cable condition) for CVT.
  * toshiba_2026_transformer_catalog.pdf -- Toshiba 6.6 kV oil-immersed
    distribution transformers (JIS C 4304:2024 / JEM 1520:2024): capacity,
    no-load loss, load loss and short-circuit impedance %Iz for 60 Hz,
    single-phase 6600/210-105 V and three-phase 6600/210 V.

Series reactance is not tabulated by Fujikura, so it is computed from the
catalogue geometry with the standard trefoil formula
    L = 0.2 * ln(GMD / GMR)  [mH/km],  GMR = 0.726 * r_conductor,
    GMD = core outer diameter (touching trefoil laid-up cores),
    X = 2*pi*f*L*1e-3  [ohm/km].
This is a derivation from archived catalogue geometry, not an external value.

Outputs (frozen, provenance-tagged):
  data/processed/engineering/cable_catalog.csv
  data/processed/engineering/transformer_catalog.csv
  data/processed/engineering/catalog_provenance.csv
"""
import hashlib
import math
import os
import re
import subprocess

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = f"{ROOT}/data/raw/engineering_sources"
OUT = f"{ROOT}/data/processed/engineering"

FUJIKURA = f"{SRC}/fujikura_6600V_CV_EE_CVT_EE.pdf"
TOSHIBA = f"{SRC}/toshiba_2026_transformer_catalog.pdf"

EXPECTED_SHA256 = {
    FUJIKURA: "021a0353d2d615a3",   # 16-hex prefix, full value written to provenance
    TOSHIBA: "734262e3e469bd60",
}

FREQ_HZ = 60.0                      # western Japan; 50 Hz variant kept in catalogue
LV_INSULATION_MM = 2.0              # 600 V class XLPE wall (assumption, labelled)
LV_SHEATH_MM = 1.5                  # 600 V class sheath wall (assumption, labelled)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pdf_text(path):
    return subprocess.run(["pdftotext", "-layout", path, "-"],
                          check=True, capture_output=True, text=True).stdout


def num(tok):
    return float(tok.replace(",", ""))


def parse_cvt(text):
    """Parse the Fujikura 6600 V CVT (E-E) construction/performance table."""
    block = text.split("■CVT（E-Eタイプ）")[1]
    rows = []
    pat = re.compile(
        r"^\s*(?:\d{1,2}\s+)?(?:\S*?\s+)??0?(\d{3,4})\s+0?(\d+\.\d)\s+(\d+\.\d)\s+(\d+\.\d)\s+(\d+\.\d)\s+"
        r"(\d+\.\d)\s+0?(\d+)\s+(\d+\.\d+)\s+")
    for line in block.splitlines():
        m = pat.match(line)
        if not m:
            continue
        area = int(m.group(1))
        cond_od = float(m.group(2))
        ins_t = float(m.group(3))
        ins_od = float(m.group(4))
        core_od = float(m.group(6))
        r20 = float(m.group(8))
        amp = num(line.split()[-1])
        rows.append(dict(area_mm2=area, conductor_od_mm=cond_od,
                         insulation_thickness_mm=ins_t, insulation_od_mm=ins_od,
                         core_od_mm=core_od, r20_ohm_per_km=r20,
                         ampacity_air40_a=amp))
        if area >= 600:
            break
    if len(rows) < 8:
        raise RuntimeError(f"CVT table parse failed: {len(rows)} rows")
    return pd.DataFrame(rows)


def reactance_ohm_per_km(conductor_od_mm, gmd_mm, freq_hz=FREQ_HZ):
    r = conductor_od_mm / 2.0
    gmr = 0.726 * r
    l_mh_per_km = 0.2 * math.log(gmd_mm / gmr)
    return 2.0 * math.pi * freq_hz * l_mh_per_km * 1e-3


def build_cable_catalog(text):
    cvt = parse_cvt(text)
    rows = []
    for _, r in cvt.iterrows():
        # MV 6.6 kV CVT: catalogue geometry directly.
        x_mv = reactance_ohm_per_km(r.conductor_od_mm, r.core_od_mm)
        rows.append(dict(
            tier="MV", system_kv=6.6, area_mm2=int(r.area_mm2), material="copper",
            r20_ohm_per_km=r.r20_ohm_per_km,
            r90_ohm_per_km=r.r20_ohm_per_km * (1 + 0.00393 * (90 - 20)),
            x_ohm_per_km=x_mv, ampacity_air40_a=r.ampacity_air40_a,
            geometry_basis="fujikura_6600V_CVT_core_od",
            provenance="fujikura_6600V_CV_EE_CVT_EE.pdf (R20, ampacity, geometry); X derived"))
        # LV 600 V class CVT: identical copper conductor, thinner wall.
        lv_core_od = r.conductor_od_mm + 2.0 * (LV_INSULATION_MM + LV_SHEATH_MM)
        x_lv = reactance_ohm_per_km(r.conductor_od_mm, lv_core_od)
        rows.append(dict(
            tier="LV", system_kv=0.21, area_mm2=int(r.area_mm2), material="copper",
            r20_ohm_per_km=r.r20_ohm_per_km,
            r90_ohm_per_km=r.r20_ohm_per_km * (1 + 0.00393 * (90 - 20)),
            x_ohm_per_km=x_lv, ampacity_air40_a=r.ampacity_air40_a,
            geometry_basis="fujikura_conductor_od + assumed 600V wall 2.0/1.5 mm",
            provenance=("fujikura_6600V_CV_EE_CVT_EE.pdf (R20, conductor OD, ampacity); "
                        "600 V wall thickness assumed; X derived")))
    return pd.DataFrame(rows)


TR_PAT = re.compile(
    r"(?:^|\s)(\d{2,4})\s+(\d{2,4})\s+(\d{3,5})\s+"
    r"(9\d\.\d\d)\s+(\d\.\d)\s+(\d\.\d\d)\s+(\d\.\d\d)\s+(\d{2,5})\s+(\d{2,5})\s+"
    r"(HC\S+)")


def build_transformer_catalog(text):
    """Parse Toshiba 6.6 kV oil-immersed transformer characteristic tables."""
    rows = []
    for line in text.splitlines():
        for m in TR_PAT.finditer(line):
            model = m.group(10)
            kva = int(m.group(1))
            if "HCR-AS" in model:
                phases, sec_v = 1, "210-105"
            elif "HCTR" in model:
                phases, sec_v = 3, "210"
            else:
                continue
            code = model.split("-")[-1]
            freq = 50.0 if code.startswith("5") else 60.0
            if "-YY" in model or "-YD" in model or "-DD" in model or "-DY" in model:
                code = model.split("-")[-2]
                freq = 50.0 if code.startswith("5") else 60.0
            if phases == 3 and "S25TB" in model:
                sec_v = "420/242" if freq == 50 else "440/254"
            rows.append(dict(model=model, phases=phases, primary_kv=6.6,
                             secondary_v=sec_v, freq_hz=freq, rating_kva=kva,
                             no_load_loss_w=int(m.group(2)),
                             load_loss_w=int(m.group(3)),
                             efficiency_pct=float(m.group(4)),
                             impedance_pct=float(m.group(5)),
                             regulation_pct=float(m.group(6)),
                             no_load_current_pct=float(m.group(7)),
                             provenance="toshiba_2026_transformer_catalog.pdf (JIS C 4304:2024)"))
    df = pd.DataFrame(rows).drop_duplicates(subset=["model"])
    if len(df) < 30:
        raise RuntimeError(f"transformer table parse failed: {len(df)} rows")
    return df.sort_values(["phases", "freq_hz", "rating_kva"]).reset_index(drop=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    prov = []
    for path, prefix in EXPECTED_SHA256.items():
        digest = sha256(path)
        if not digest.startswith(prefix):
            raise RuntimeError(f"checksum mismatch for {path}: {digest}")
        prov.append(dict(source=os.path.basename(path), sha256=digest,
                         bytes=os.path.getsize(path)))
    cables = build_cable_catalog(pdf_text(FUJIKURA))
    trafos = build_transformer_catalog(pdf_text(TOSHIBA))
    cables.to_csv(f"{OUT}/cable_catalog.csv", index=False)
    trafos.to_csv(f"{OUT}/transformer_catalog.csv", index=False)
    pd.DataFrame(prov).to_csv(f"{OUT}/catalog_provenance.csv", index=False)
    print("cable rows", len(cables), "transformer rows", len(trafos))
    print(cables[cables.tier == "MV"][["area_mm2", "r90_ohm_per_km", "x_ohm_per_km",
                                       "ampacity_air40_a"]].head(8).to_string(index=False))
    print(trafos[(trafos.phases == 3) & (trafos.freq_hz == 60)]
          [["rating_kva", "no_load_loss_w", "load_loss_w", "impedance_pct"]]
          .head(10).to_string(index=False))


if __name__ == "__main__":
    main()
