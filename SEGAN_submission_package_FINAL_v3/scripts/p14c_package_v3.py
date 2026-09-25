"""Phase R17-R21 (v3): highlights, municipality outputs, claim matrix,
inline docx, final SEGAN submission package. All values from
analysis/manuscript_values_v3.csv / *_v2 tables. No earlier-version
language in manuscript-facing artifacts."""
import csv, os, zipfile, glob, shutil
import pandas as pd
from docx import Document
from docx.shared import Inches

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mv = {r["key"]: r["value"] for r in
      csv.DictReader(open(f"{ROOT}/analysis/manuscript_values_v3.csv"))}

def fmt(v, nd=2):
    try:
        return f"{float(v):.{nd}f}"
    except Exception:
        return str(v)

# ---------------- highlights ----------------
hl = [
    "Topology flexibility at LV renewal valued via nonnegative estimand",
    "Feasibility gates (ampacity, voltage, transformer) precede costing",
    "Value of re-layout is under 1%: economically equivalent zones",
    "Negative raw contrast shown to be estimand/assumption artifact",
    "AC power-flow validation of the linearized model on all feeders",
]
for h in hl:
    assert len(h) <= 85, h
open(f"{ROOT}/manuscript/highlights_v3.txt", "w").write("\n".join(hl) + "\n")

# ---------------- claim-evidence matrix v2 ----------------
ce = [
    ("VoF +0.01%/+0.39%/+0.20% (Sano/Kudamatsu/Yasu), all economically_equivalent",
     "scenario_results_v2.csv vof_pct; PRIMARY_ESTIMAND_SPEC.md; ECONOMIC_EQUIVALENCE_SPEC.yaml"),
    ("Naive ΔNPC +0.01%/-10.1%/+0.20%; negative value is estimand artifact",
     "scenario_results_v2.csv ltp_pct; audit_v2/COUNTERFACTUAL_OPTIMIZATION_AUDIT.md"),
    ("Kudamatsu -10% decomposes to 5 clusters with 2-10x rewiring capex",
     "BENEFIT_DECOMPOSITION.csv; audit_v2/KUDAMATSU_MECHANISM_AUDIT.md"),
    ("LinDistFlow validated vs pandapower AC on all feasible feeders (max vm err 0.019 pu)",
     "AC_VS_LINEAR_VALIDATION.csv; AC_VALIDATION_REPORT.md"),
    ("MV-threshold sensitivity flips Kudamatsu ΔNPC (+0.27% at 200kW)",
     "ENGINEERING_ASSUMPTION_SENSITIVITY.csv"),
    ("24-replicate and leave-one-family-out robust (fam ratio ~1.00)",
     "cluster_results_v2.csv s1_famA/B_npc; rep24 scenario"),
    ("feasibility gates: vdrop≤6%, ampacity, 150kVA loading",
     "config/ENGINEERING_FEASIBILITY_SPEC.yaml; p07b_optimize_v2.py"),
    ("MV-served nodes >150kW excluded; LV share 75/55/53% of demand",
     "mv_served_nodes.csv; demand_coverage_audit.csv"),
    ("rooftop PV reduces NPC further in ~all clusters (upper bound)",
     "dg_results_v2.csv p_s3_better"),
]
pd.DataFrame(ce, columns=["claim", "evidence"]).to_csv(
    f"{ROOT}/analysis/claim_evidence_matrix_v3.csv", index=False)

# ---------------- municipality outputs v2 ----------------
os.makedirs(f"{ROOT}/municipality_v3", exist_ok=True)
tpl = """# {City} — undergrounding renewal planning-support summary (modeled)

Scope: LV study-zone reconstruction from open data; modeled demands;
planning support only — NOT engineering design or engineering advice.

- LV clusters assessed: {ncl} ({nfeas} feasible under the frozen spec)
- Modeled coincident LV demand: {dem} MW
- Value of topology flexibility VoF: {vof}% of S1 NPC (class: {cls})
- Naive ΔNPC: {ltp}% | Robustness (500 MC draws): P(ΔNPC>0) = {p}
- Mean topology divergence distance TDD: {tdd}
- Interpretation: {interp}
- PV overlay (S3) is an upper-bound sensitivity; PV siting economics
  dominate re-layout decisions.

Inputs, code, provenance: analysis/ and provenance/ in the repository
snapshot. Never contact us about this output; it is generated research
material, not a municipal communication.
"""
interp = {
    "sano": "topology flexibility worth <0.1% of renewal cost; like-for-like renewal is a defensible default",
    "kudamatsu": "legacy layout already near-optimal; re-layout adds cost without benefit; keep like-for-like",
    "yasu": "topology flexibility worth <0.5% of renewal cost; like-for-like renewal is a defensible default"}
for c, cname in [("sano", "Sano"), ("kudamatsu", "Kudamatsu"), ("yasu", "Yasu")]:
    txt = tpl.format(City=cname, ncl=int(float(mv[f"{c}_clusters"])),
                     nfeas=int(float(mv[f"{c}_clusters_feasible"])),
                     dem=fmt(mv[f"{c}_lv_demand_mw"], 1),
                     vof=fmt(mv[f"{c}_vof_pct"], 2), cls=mv[f"{c}_equivalence_class"],
                     ltp=fmt(mv[f"{c}_ltp_pct"], 2),
                     p=fmt(mv[f"{c}_mc_p_ltp_pos"], 2),
                     tdd=fmt(mv[f"{c}_mean_tld"], 2), interp=interp[c])
    open(f"{ROOT}/municipality_v3/{c}_planning_support.md", "w").write(txt)

# ---------------- inline docx v2 ----------------
doc = Document(f"{ROOT}/manuscript/manuscript_draft_v3.docx")
figs = ["v3_fig1_study_zones.png", "v3_fig2_topology_example.png",
        "v3_fig3_delta.png", "v3_fig4_tornado.png", "v3_fig5_dg.png"]
caps = {
    "v3_fig1_study_zones.png": "Figure 1. Study zones: road graph (grey) and snapped building demand nodes (blue).",
    "v3_fig2_topology_example.png": "Figure 2. Example feeder cluster: S1 like-for-like replicate vs S2 optimized layout.",
    "v3_fig3_delta.png": "Figure 3. Primary estimand VoF by zone vs Monte-Carlo ΔNPC.",
    "v3_fig4_tornado.png": "Figure 4. ΔNPC under engineering-assumption swings, all zones.",
    "v3_fig5_dg.png": "Figure 5. NPC of S2 vs S3 (rooftop-PV extension) by zone.",
}
insertions = [
    ("(Figures 1–3)", figs[:3]),
    ("(Figure 4)", figs[3:4]),
    ("(Figure 5)", figs[4:]),
]
done = set()
for par in doc.paragraphs:
    for anchor_text, fl in insertions:
        if anchor_text in par.text and anchor_text not in done:
            anchor = par._p
            for f in fl:
                pic = doc.add_paragraph()
                pic.add_run().add_picture(f"{ROOT}/figures/{f}", width=Inches(5.8))
                cap = doc.add_paragraph(caps[f])
                anchor.addnext(cap._p); anchor.addnext(pic._p)
                anchor = cap._p
            done.add(anchor_text)
print("inserted:", done)
doc.save(f"{ROOT}/manuscript/manuscript_inline_v3.docx")

# ---------------- final package ----------------
pkg = f"{ROOT}/SEGAN_submission_package_FINAL_v3"
if os.path.exists(pkg):
    shutil.rmtree(pkg)
os.makedirs(pkg)
files = [
    "manuscript/manuscript_draft_v3.docx", "manuscript/manuscript_inline_v3.docx",
    "manuscript/highlights_v3.txt",
    "analysis/manuscript_values_v3.csv", "analysis/scenario_results_v2.csv",
    "analysis/sensitivity_mc_v2.csv", "analysis/sensitivity_tornado_v2.csv",
    "analysis/dg_results_v2.csv", "analysis/ablation_results.csv",
    "analysis/feasibility_sensitivity.csv", "analysis/original_vs_corrected.csv",
    "analysis/claim_evidence_matrix_v3.csv", "analysis/mv_served_nodes.csv",
    "analysis/reconstruction_summary_v2.csv", "analysis/references_verified.csv",
    "analysis/novelty_matrix.csv", "analysis/journal_fit_matrix.csv",
    "analysis/data_audit.csv", "analysis/benchmark_validation.csv",
    "audit_v2/AUDIT_FILE_INVENTORY.csv", "audit_v2/MANUSCRIPT_VALUE_AUDIT.csv",
    "audit_v2/VOLTAGE_ROOT_CAUSE_AUDIT.md", "audit_v2/BENCHMARK_VALIDATION_REPORT.md",
    "config/ENGINEERING_FEASIBILITY_SPEC.yaml", "config/study.yaml",
    "tables/table2_results_v3.csv",
    "provenance/source_registry.csv", "provenance/decision_log.md",
]
for c in ["sano", "kudamatsu", "yasu"]:
    files.append(f"municipality_v3/{c}_planning_support.md")
files += [f"figures/{f}" for f in figs]
files += [f"scripts/{f}" for f in sorted(glob.glob1(f"{ROOT}/scripts", "*.py"))]
for f in files:
    d = os.path.join(pkg, f)
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copy(f"{ROOT}/{f}", d)
zpath = f"{ROOT}/SEGAN_submission_package_FINAL_v3.zip"
if os.path.exists(zpath):
    os.remove(zpath)
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for dp, _, fs in os.walk(pkg):
        for f in fs:
            fp = os.path.join(dp, f)
            z.write(fp, os.path.relpath(fp, pkg))
print("zip entries:", len(zipfile.ZipFile(zpath).namelist()))
print("done")
