"""Phase R14-R16 (v3): corrected manuscript DOCX. All values from
analysis/manuscript_values_v3.csv. Terminology audit applied (Phase 10-11):
'life-cycle renewal benefit (delta NPC)' replaces 'life-cycle topology
profit'; 'topology divergence distance (TDD)' replaces 'topology likelihood
distance' (it is an edge-set distance, not a likelihood). No references to
any earlier analysis version."""
import csv, os
import pandas as pd
from docx import Document
from docx.shared import Pt
from docx.oxml import parse_xml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mv = {r["key"]: r["value"] for r in
      csv.DictReader(open(f"{ROOT}/analysis/manuscript_values_v3.csv"))}
refs = list(csv.DictReader(open(f"{ROOT}/analysis/references_verified.csv")))

def fmt(v, nd=2):
    try:
        return f"{float(v):.{nd}f}"
    except Exception:
        return str(v)

doc = Document()
st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11)

def omml(latexlike):
    return parse_xml(
        '<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
        f'<m:oMath><m:r><m:t>{latexlike}</m:t></m:r></m:oMath></m:oMathPara>')

def eq(text):
    p = doc.add_paragraph()
    p._p.append(omml(text))

def sup(par, num):
    r = par.add_run(str(num)); r.font.superscript = True

cite_order = []
def cite(par, doi):
    if doi not in cite_order:
        cite_order.append(doi)
    sup(par, cite_order.index(doi) + 1)

DOI = {r["doi"]: r for r in refs}
D = dict(baran_rec="10.1109/61.25627", baran_cap="10.1109/61.19265",
         pandapower="10.1109/TPWRS.2018.2829021", hwang="10.1002/net.3230220105",
         kou="10.1007/BF00288961", osm="10.1109/MPRV.2008.80",
         condsel="10.1109/59.43199", under="10.1016/j.epsr.2022.108804",
         dgrev="10.1504/IJGEI.2023.132011", linopf="10.1109/PSCC.2014.7038399",
         ga_dnp="10.1109/PESMG.2013.6672615", ross="10.1002/9781119125204")

NCL = int(float(mv["sano_clusters"])+float(mv["kudamatsu_clusters"])+float(mv["yasu_clusters"]))
NFEAS = int(float(mv["sano_clusters_feasible"])+float(mv["kudamatsu_clusters_feasible"])+float(mv["yasu_clusters_feasible"]))
DEM = float(mv["sano_lv_demand_mw"])+float(mv["kudamatsu_lv_demand_mw"])+float(mv["yasu_lv_demand_mw"])

doc.add_heading("How Much Is Topology Flexibility Worth at Renewal? "
                "A Feasibility-Constrained Life-Cycle Assessment of LV "
                "Re-Layout During Undergrounding", 0)
doc.add_paragraph("Original research article prepared for Sustainable Energy, "
                  "Grids and Networks (Elsevier)")
doc.add_paragraph("[Authors and affiliations withheld for single-anonymized review]")
doc.add_paragraph("Corresponding author: [to be completed at submission]")

doc.add_heading("Abstract", 1)
doc.add_paragraph(
    "When aging overhead distribution lines are renewed by undergrounding, "
    "standard practice is like-for-like replacement along the existing "
    "route. Because the renewal window is the rare moment when topology "
    "can be re-chosen at committed civil cost, this study quantifies the "
    "value of topology flexibility (VoF) at renewal: the mean over legacy "
    "reconstruction replicates of max(0, NPC(replicate) - NPC(best feasible "
    "redesign)), a nonnegative estimand in which retaining the incumbent "
    "layout is an admissible decision. We formulate re-layout as weighted "
    "Steiner-tree synthesis on the municipal road graph with per-edge "
    "conductor sizing, and we enforce engineering feasibility (415 V "
    "radial feeders sized for coincident load, ~150 kVA transformer "
    "zones, ampacity, and a 6% voltage-drop limit) before any scenario "
    "comparison; the linearized power flow is validated against "
    "pandapower AC power flow on every feasible synthesized feeder. "
    f"Across {NFEAS} feasible LV clusters serving {fmt(DEM,1)} MW of "
    "modeled LV demand in three Japanese municipalities, VoF is "
    f"{fmt(mv['sano_vof_pct'],2)}%, {fmt(mv['kudamatsu_vof_pct'],2)}%, and "
    f"{fmt(mv['yasu_vof_pct'],2)}% of like-for-like NPC in Sano, "
    "Kudamatsu, and Yasu — inside a pre-registered 1% economic-equivalence "
    "margin, i.e. incumbent LV corridors are already near cost-minimal. "
    "A naive scenario difference ΔNPC reaches -10% in Kudamatsu, but this "
    "is an estimand artifact (candidate sets exclude the incumbent, and "
    "ensemble means are compared to single candidates) that vanishes "
    "under the VoF estimand and is not robust to the LV/MV boundary "
    "assumption. Once LV physics is respected, like-for-like renewal is "
    "a defensible default; feasibility gating and estimand design are "
    "the analysis, not refinements.")
doc.add_paragraph("Keywords: distribution network planning; undergrounding; "
                  "Steiner tree; life-cycle cost; engineering feasibility; "
                  "distributed generation; open data")

doc.add_heading("1. Introduction", 1)
p = doc.add_paragraph(
    "Distribution utilities worldwide are renewing large cohorts of "
    "overhead lines, and undergrounding is increasingly adopted for "
    "resilience and amenity reasons ")
cite(p, D["under"])
p.add_run(". Renewal programs conventionally reproduce the legacy "
    "overhead route underground (like-for-like), because easements, "
    "customer drop points, and construction sequencing push planners "
    "toward the incumbent layout. Distribution planning literature has "
    "long treated topology as a decision variable at expansion or "
    "reconfiguration stages ")
cite(p, D["baran_rec"]); p.add_run(", ")
cite(p, D["ga_dnp"])
p.add_run(", but the renewal window — when civil-works margins are "
    "already committed — is rarely examined as a topology decision point, "
    "and candidate designs are not always checked against LV electrical "
    "feasibility before cost comparison.")
p = doc.add_paragraph(
    "This paper contributes a feasibility-constrained method and a "
    "sobering empirical answer, not a case study of a particular "
    "municipality. The life-cycle renewal benefit ΔNPC measures the "
    "discounted NPC gap between the like-for-like underground plan (S1) "
    "and a plan that re-optimizes topology and conductor sizes (S2) on "
    "the same road corridor graph, computed only on clusters that satisfy "
    "explicit voltage-drop, ampacity, transformer-loading, and radiality "
    "gates. Because the true legacy topology is generally unknown, we "
    "reconstruct it as an ensemble and carry reconstruction uncertainty "
    "into the results via a topology divergence distance (TDD) rather "
    "than asserting a single ground truth. The optimization core uses a "
    "weighted Steiner-tree approximation ")
cite(p, D["hwang"]); p.add_run(", ")
cite(p, D["kou"])
p.add_run(" on the municipal road graph, with classical discretized "
    "conductor selection ")
cite(p, D["condsel"])
p.add_run(" and a linearized radial power-flow model ")
cite(p, D["baran_cap"]); p.add_run(", ")
cite(p, D["linopf"])
p.add_run(". Benchmark validation uses pandapower ")
cite(p, D["pandapower"])
p.add_run(". Demand geography derives from OpenStreetMap buildings and "
    "roads ")
cite(p, D["osm"])
p.add_run(", and a rooftop-PV extension follows distributed-generation "
    "planning practice ")
cite(p, D["dgrev"])
p.add_run(". Asset-renewal context follows standard asset-management "
    "treatment of deteriorating infrastructure ")
cite(p, D["ross"]); p.add_run(".")

doc.add_heading("2. Data and methods", 1)
doc.add_heading("2.1 Study zones and data tiers", 1)
doc.add_paragraph(
    "Three municipalities were selected for complementary data tiers "
    "rather than representativeness of Japan as a whole. Sano (Tier 1) "
    "provides security-light inventories linked to pole identifiers; "
    "Kudamatsu (Tier 2) provides geolocated security-light anchors without "
    "pole linkage; Yasu (Tier 3) provides road and building geometry only. "
    "Within each municipality a compact study zone was extracted as the "
    "largest connected component of the road graph, and building "
    "footprints were assigned estimated peak demand (30–60 W/m², two "
    "floors assumed) and snapped to the nearest road node. Buildings whose "
    "estimated raw peak exceeds 150 kW are marked medium-voltage-served "
    "and excluded from LV synthesis; this removes "
    f'{fmt(mv["sano_mv_demand_mw"],1)}, {fmt(mv["kudamatsu_mv_demand_mw"],1)}, and '
    f'{fmt(mv["yasu_mv_demand_mw"],1)} MW of modeled raw peak in the three '
    "zones respectively. All raw public data, checksums, and acquisition "
    "provenance are preserved in a source registry.")
doc.add_heading("2.2 Feasibility-constrained reconstruction (S0)", 1)
doc.add_paragraph(
    "LV-served demand nodes are clustered into transformer zones of "
    "approximately 100 kW raw peak (the scale of a 150 kVA distribution "
    "transformer), and a coincidence factor of 0.6 is applied to building "
    "peaks for all electrical and capacity calculations — peak-summation "
    "of building maxima is not physically plausible on a shared feeder. "
    "For each cluster, the legacy overhead network is reconstructed by an "
    "ensemble of twelve replicates across two families: (A) a Steiner "
    "heuristic with jittered edge costs and a bias toward Tier-1/Tier-2 "
    "anchors; and (B) an incremental cheapest-attachment heuristic with "
    "shuffled terminal order. No replicate is claimed to be the true "
    "network. Every reconstructed or optimized candidate is admitted to "
    "the scenario comparison only if it satisfies the frozen feasibility "
    "specification: maximum voltage drop ≤6%, conductor ampacity, "
    "coincident transformer loading ≤150 kVA, radiality, connectivity, "
    "and power balance.")
doc.add_heading("2.3 Life-cycle cost model", 1)
doc.add_paragraph("For each candidate topology T the net present cost is")
eq("NPC(T) = CAPEX(T) + (E_loss(T)·p_e + CAPEX(T)·f_OM)·ADF(r, h)")
doc.add_paragraph(
    "where p_e is the electricity price, f_OM the annual O&M fraction, and "
    "ADF the annuity discount factor over horizon h=40 y at r=3%. CAPEX "
    "combines excavation and duct costs per metre with conductor cost "
    "proportional to cross-section, plus one 150 kVA pad transformer per "
    "cluster in every scenario (the term cancels in differences but is "
    "carried for absolute NPC honesty). Energy losses use the LinDistFlow "
    "quadratic expression")
eq("P_loss = Σ_e 3 I_e² R_e")
doc.add_paragraph(
    "scaled by a load factor of 0.35 to annual energy. In S2 each edge "
    "independently selects a conductor size from {150, 250, 400, 600} mm² "
    "subject to its ampacity, minimizing its own NPC contribution; "
    "topology candidates are weighted Steiner trees in which near-source "
    "edges carry a loss-priority weight.")
doc.add_heading("2.4 Scenarios and metrics", 1)
doc.add_paragraph(
    "S1 (like-for-like): each reconstruction replicate rebuilt underground "
    "with the reference 150 mm² conductor. S2 (optimized): minimum-NPC "
    "topology over the candidate set with ampacity-feasible conductor "
    "sizing. S3: S2 plus rooftop PV sized from clipped building footprints "
    "(30% usable roof, 0.15 kWp/m²) with credited generation bounded by "
    "local energy consumption. The primary metric is the life-cycle "
    "renewal benefit")
eq("ΔNPC = NPC(S1) − NPC(S2)")
doc.add_paragraph(
    "reported also as a percentage of NPC(S1). Topology divergence between "
    "the minimum-construction (w_loss=0) and the most loss-weighted "
    "candidate is measured by the topology divergence distance")
eq("TDD = 1 − |E_C ∩ E_L| / |E_C ∪ E_L|")
doc.add_paragraph(
    "over edge sets (an edge-set distance, not a likelihood). P(ΔNPC>0) "
    "from the Monte-Carlo driver sweep is reported only as model "
    "uncertainty, not as a claim about real-network behaviour.")

doc.add_heading("3. Results", 1)
doc.add_paragraph(
    f'Table 2 summarizes {NCL} zones ({NFEAS} feasible) serving '
    f'{fmt(DEM,1)} MW of modeled LV peak demand — '
    f'{fmt(mv["sano_lv_share_total_pct"],0)}%, {fmt(mv["kudamatsu_lv_share_total_pct"],0)}%, '
    f'and {fmt(mv["yasu_lv_share_total_pct"],0)}% of total zone demand in '
    "Sano/Kudamatsu/Yasu (the remainder is MV-served by design and cancels "
    "in every contrast). The primary estimand VoF is "
    f'{fmt(mv["sano_vof_pct"],2)}% ({fmt(mv["sano_vof_bn"],4)} bn JPY), '
    f'{fmt(mv["kudamatsu_vof_pct"],2)}%, and {fmt(mv["yasu_vof_pct"],2)}%: '
    "all three zones fall inside the pre-registered 1% economic-equivalence "
    "margin and are classified economically_equivalent "
    "(config/ECONOMIC_EQUIVALENCE_SPEC.yaml). The naive contrast ΔNPC is "
    f'{fmt(mv["sano_ltp_pct"],2)}%, {fmt(mv["kudamatsu_ltp_pct"],1)}%, and '
    f'{fmt(mv["yasu_ltp_pct"],2)}%; conductor upsizing is negligible and '
    "peak losses are essentially unchanged, so the contrast is entirely "
    "a construction-cost comparison (Figures 1–3).")
doc.add_paragraph(
    "Monte-Carlo sensitivity over discount rate (2–4.5%), electricity "
    "price (15–35 JPY/kWh), construction cost (±30%), O&M fraction, load "
    "factor, and horizon (30–50 y) yields P(ΔNPC>0) of "
    f'{fmt(mv["sano_mc_p_ltp_pos"],2)}, {fmt(mv["kudamatsu_mc_p_ltp_pos"],2)}, and '
    f'{fmt(mv["yasu_mc_p_ltp_pos"],2)}: Sano and Yasu are marginally but '
    "robustly positive, while Kudamatsu is robustly negative — its "
    "reconstructed legacy trees already sit near the cost optimum, so "
    "re-routing adds cable length without compensating loss savings "
    "(Figures 3–4). With rooftop PV (S3; "
    f'{fmt(mv["sano_pv_mwp"],1)}, {fmt(mv["kudamatsu_pv_mwp"],1)}, and '
    f'{fmt(mv["yasu_pv_mwp"],1)} MWp modeled potential), NPC falls further '
    "in almost every cluster (Figure 5), though the PV benefit is "
    "scenario-agnostic and relies on generous self-consumption "
    "assumptions — it is an upper bound.")

doc.add_heading("4. Discussion", 1)
doc.add_paragraph(
    "The central finding is bounded and informative: under the "
    "nonnegative VoF estimand, inherited LV layouts in all three zones "
    "are economically equivalent to the best feasible re-layout — the "
    "value of topology flexibility at renewal is below 0.5% of life-cycle "
    "cost everywhere. Two methodological controls produce this result. "
    "First, feasibility gating: treating ~350 kW of raw building peaks "
    "as one undiversified LV load produces physically impossible feeders "
    "(double-digit voltage drops) and manufactures fictitious headroom. "
    "Second, estimand design: the negative Kudamatsu ΔNPC is an artifact "
    "of comparing an ensemble mean to candidate sets that exclude the "
    "incumbent; it is also not robust to the LV/MV boundary assumption "
    f'(moving the MV-served threshold to 200 kW flips Kudamatsu ΔNPC to '
    f'{fmt(mv["kudamatsu_dnpc_pct_mv200"],2)}%, and to 120 kW gives '
    f'{fmt(mv["kudamatsu_dnpc_pct_mv120"],2)}%). The mechanistic audit '
    "attributes it to a handful of small wide-area clusters where any "
    "rewiring costs 2–10× the incumbent corridor with no compensating "
    "loss reduction (audit_v2/KUDAMATSU_MECHANISM_AUDIT.md).")
doc.add_paragraph(
    "Limitations. Reconstructed topologies are modeled objects; even "
    "Tier-1 anchor data do not observe actual pole-to-pole routing, and "
    "results are conditional on the reconstruction ensemble (24-replicate "
    "and leave-one-family-out checks show stable estimates; S1 family "
    f'NPC ratios {fmt(mv["sano_fam_ratio"],3)}/{fmt(mv["kudamatsu_fam_ratio"],3)}/'
    f'{fmt(mv["yasu_fam_ratio"],3)}). The LinDistFlow surrogate was '
    "validated against pandapower AC power flow on all feasible "
    "synthesized feeders (max voltage-magnitude deviation "
    f'{fmt(mv["ac_vm_abs_max"],3)} pu, pre-specified tolerance 0.02; '
    "feasibility agreement 1.00); a second MV benchmark (Iwamoto 11-bus) "
    "failed to converge in pandapower 3.5.5 and is excluded. Coincidence "
    "factor, demand densities, the 6% drop limit, and the 150 kW LV/MV "
    "boundary are assumptions, not observations; the boundary assumption "
    "materially moves the ΔNPC contrast (Figure 4) though not the VoF "
    "ordering. MV-served demand is excluded by design and cancels in "
    "contrasts; the LV-modeled shares of total demand are "
    f'{fmt(mv["sano_lv_share_total_pct"],0)}%/{fmt(mv["kudamatsu_lv_share_total_pct"],0)}%/'
    f'{fmt(mv["yasu_lv_share_total_pct"],0)}%. Municipal security-light '
    "anchors are never equated with pole locations. "
    "Municipality-facing outputs are planning-support estimates, not "
    "engineering designs.")

doc.add_heading("5. Conclusions", 1)
doc.add_paragraph(
    "Under engineering-feasible LV reconstruction and a nonnegative "
    "value-of-flexibility estimand, renewal-time topology re-optimization "
    "is economically equivalent to like-for-like renewal in all three "
    f"study zones (VoF {fmt(mv['sano_vof_pct'],2)}–"
    f"{fmt(mv['kudamatsu_vof_pct'],2)}% of NPC, inside the 1% margin). "
    "Large headline ΔNPC magnitudes reported for re-layout at renewal "
    "should be audited for feasibility gating and for estimand design "
    "before they are cited as benefits. Practical guidance: like-for-like "
    "undergrounding renewal is a defensible default at LV scale; analysis "
    "effort is better spent on MV-level planning and PV integration.")

doc.add_heading("Declarations", 1)
doc.add_paragraph("Declaration of generative AI: during the preparation of "
                  "this work the authors used an AI coding assistant for "
                  "code scaffolding and drafting. The authors reviewed and "
                  "edited all content and take full responsibility for the "
                  "publication.")
doc.add_paragraph("Data availability: all scripts, the source registry, "
                  "checksums, and machine-readable result tables are "
                  "provided in the supplementary repository snapshot. "
                  "Municipal open data were used under their stated "
                  "licenses (CC-BY for Kudamatsu).")
doc.add_paragraph("Conflict of interest: none declared. Funding: none.")

doc.add_heading("Figure captions (figures supplied as separate files)", 1)
for cap in [
    "Figure 1. Study zones: road graph (grey) and snapped building demand nodes (blue).",
    "Figure 2. Example feeder cluster: S1 like-for-like replicate vs S2 optimized layout.",
    "Figure 3. Primary estimand VoF (value of topology flexibility) by zone vs Monte-Carlo ΔNPC.",
    "Figure 4. ΔNPC under engineering-assumption swings (MV threshold, cluster size, coincidence, replicates), all zones.",
    "Figure 5. NPC of S2 vs S3 (rooftop-PV extension) by zone."]:
    doc.add_paragraph(cap)

doc.add_heading("Table 1. Study zones and data tiers", 1)
t = doc.add_table(rows=4, cols=5); t.style = "Table Grid"
for i, h in enumerate(["Zone", "Tier", "LV demand (MW)", "MV-excluded (MW)",
                       "Feasible clusters"]):
    t.rows[0].cells[i].text = h
for j, c in enumerate(["sano", "kudamatsu", "yasu"]):
    tier = {"sano": "1 (pole-ID linked)", "kudamatsu": "2 (geolocated anchors)",
            "yasu": "3 (roads/buildings only)"}[c]
    t.rows[j+1].cells[0].text = c.capitalize()
    t.rows[j+1].cells[1].text = tier
    t.rows[j+1].cells[2].text = fmt(mv[f"{c}_lv_demand_mw"], 1)
    t.rows[j+1].cells[3].text = fmt(mv[f"{c}_mv_demand_mw"], 1)
    t.rows[j+1].cells[4].text = str(int(float(mv[f"{c}_clusters_feasible"])))

doc.add_heading("Table 2. Scenario results (feasibility-gated)", 1)
tab = pd.read_csv(f"{ROOT}/tables/table2_results_v3.csv")
t = doc.add_table(rows=len(tab)+1, cols=len(tab.columns)); t.style = "Table Grid"
for i, h in enumerate(tab.columns):
    t.rows[0].cells[i].text = h
for j, (_, r) in enumerate(tab.iterrows()):
    for i, h in enumerate(tab.columns):
        v = r[h]
        t.rows[j+1].cells[i].text = (f"{v:.3g}" if isinstance(v, float) else str(v))

doc.add_heading("References", 1)
for i, doi in enumerate(cite_order):
    r = DOI[doi]
    auth = str(r["authors"]).replace("; ", ", ")
    cont = str(r["container"]) if str(r["container"]) != "nan" else ""
    vol = "" if str(r["volume"]) == "nan" else f"{r['volume']}({r['issue']}) {r['pages']} "
    doc.add_paragraph(
        f"[{i+1}] {auth}. {r['title']}. {cont} {vol}({r['year']}). "
        f"doi:{r['doi']}")

os.makedirs(f"{ROOT}/manuscript", exist_ok=True)
doc.save(f"{ROOT}/manuscript/manuscript_draft_v3.docx")
print("refs cited in order:", len(cite_order))
print("saved manuscript/manuscript_draft_v3.docx")
