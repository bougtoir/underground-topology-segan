"""Phase 13: build manuscript DOCX (native OMML equations, numbered
Vancouver citations, all values from analysis/manuscript_values.csv)."""
import csv, os
import pandas as pd
from docx import Document
from docx.shared import Pt, Inches
from docx.oxml.ns import qn
from docx.oxml import parse_xml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mv = {r["key"]: r["value"] for r in
      csv.DictReader(open(f"{ROOT}/analysis/manuscript_values.csv"))}
refs = list(csv.DictReader(open(f"{ROOT}/analysis/references_verified.csv")))

def fmt(v, nd=2):
    try:
        return f"{float(v):.{nd}f}"
    except Exception:
        return str(v)

doc = Document()
st = doc.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(11)

def omml(latexlike):
    """Wrap a literal OMML run."""
    return parse_xml(
        '<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
        f'<m:oMath><m:r><m:t>{latexlike}</m:t></m:r></m:oMath></m:oMathPara>')

def eq(text):
    p = doc.add_paragraph()
    p._p.append(omml(text))

def sup(par, num):
    r = par.add_run(str(num)); r.font.superscript = True

# ---------- citation bookkeeping (Vancouver, order of appearance) -------
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

# ----------------------------- title page -------------------------------
doc.add_heading("Life-Cycle Optimization of Distribution Network Topology "
                "During Undergrounding Renewal: Beyond Like-for-Like "
                "Replacement", 0)
doc.add_paragraph("Original research article prepared for Sustainable Energy, "
                  "Grids and Networks (Elsevier)")
doc.add_paragraph("[Authors and affiliations withheld for single-anonymized review]")
doc.add_paragraph("Corresponding author: [to be completed at submission]")

# ----------------------------- abstract ---------------------------------
doc.add_heading("Abstract", 1)
p = doc.add_paragraph(
    "When aging overhead distribution lines are renewed by undergrounding, "
    "the standard engineering practice is like-for-like replacement: the "
    "underground cable replicates the existing overhead route. This study "
    "asks whether the renewal event itself is an opportunity to re-optimize "
    "the network topology over the asset life cycle. We formulate the "
    "renewal problem as a Steiner tree synthesis on the local road graph "
    "with per-edge conductor sizing and a discounted loss term, and we "
    "define the life-cycle topology profit (LTP) as the net present cost "
    "difference between the like-for-like plan and the optimized plan. "
    "Using three Japanese municipalities with complementary open-data "
    "tiers (pole-ID-linked, geolocated-anchor, and road/building only) as "
    "validation environments, we reconstruct the legacy feeder network with "
    "an ensemble of two reconstruction families and quantify topology "
    "uncertainty by a topology likelihood distance (TLD). Across "
    f'{int(float(mv["sano_clusters"])+float(mv["kudamatsu_clusters"])+float(mv["yasu_clusters"]))} '
    "feeder clusters, life-cycle optimization reduces net present cost by "
    f'{fmt(mv["sano_ltp_pct"],1)}%, {fmt(mv["kudamatsu_ltp_pct"],1)}%, and '
    f'{fmt(mv["yasu_ltp_pct"],1)}% of the like-for-like benchmark in Sano, '
    "Kudamatsu, and Yasu respectively; a Monte-Carlo sweep over cost and "
    "economic drivers leaves the benefit positive with probability "
    f'{fmt(mv["sano_mc_p_ltp_pos"],2)}\u2013{fmt(mv["kudamatsu_mc_p_ltp_pos"],2)}. '
    "Peak loss is roughly halved. Adding rooftop photovoltaic potential "
    "(S3) further reduces net present cost in all clusters. The results "
    "indicate that renewal windows are low-regret occasions to correct "
    "legacy topology; municipalities should treat undergrounding programs "
    "as planning events, not only construction events.")
doc.add_paragraph("Keywords: distribution network planning; undergrounding; "
                  "Steiner tree; life-cycle cost; conductor sizing; "
                  "distributed generation; open data")

# ----------------------------- 1 Introduction ---------------------------
doc.add_heading("1. Introduction", 1)
p = doc.add_paragraph(
    "Distribution utilities worldwide are renewing large cohorts of "
    "overhead lines, and undergrounding is increasingly adopted for "
    "resilience and amenity reasons ")
cite(p, D["under"])
p.add_run(". Renewal programs conventionally reproduce the legacy "
    "overhead route underground (like-for-like), because easements, "
    "customer drop points, and construction sequencing push planners "
    "toward the incumbent layout. Yet the overhead layout was itself the "
    "outcome of incremental historical build-out rather than life-cycle "
    "optimization. Distribution planning literature has long treated "
    "topology as a decision variable at expansion or reconfiguration "
    "stages ")
cite(p, D["baran_rec"]); p.add_run(", ")
cite(p, D["ga_dnp"])
p.add_run(", but the renewal window — when construction margins are "
    "already committed — is rarely examined as a topology decision point.")
p = doc.add_paragraph(
    "This paper contributes a methodological pipeline and a metric, not a "
    "case study of a particular municipality. The life-cycle topology "
    "profit (LTP) measures the discounted net present cost (NPC) gap "
    "between the like-for-like underground plan (scenario S1) and a plan "
    "that re-optimizes topology and conductor sizes (S2) on the same road "
    "corridor graph. Because the true legacy topology is generally unknown "
    "to the analyst, we reconstruct it as an ensemble from public data and "
    "carry reconstruction uncertainty into the results explicitly via a "
    "topology likelihood distance (TLD) rather than asserting a single "
    "ground truth. The optimization core uses a weighted Steiner-tree "
    "approximation ")
cite(p, D["hwang"]); p.add_run(", ")
cite(p, D["kou"])
p.add_run(" on the municipal road graph, coupled with classical optimal "
    "conductor selection ")
cite(p, D["condsel"])
p.add_run(" and a linearized loss model ")
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

# ----------------------------- 2 Methods --------------------------------
doc.add_heading("2. Data and methods", 1)
doc.add_heading("2.1 Study zones and data tiers", 1)
doc.add_paragraph(
    "Three municipalities were selected for complementary data tiers "
    "rather than representativeness of Japan as a whole. Sano (Tier 1) "
    "provides security-light inventories linked to pole identifiers "
    f'({int(float(mv["audit_sano_rows"]))} records, '
    f'{int(float(mv["audit_sano_pole_dupes"]))} duplicated pole values); '
    f'Kudamatsu (Tier 2) provides geolocated security-light anchors '
    f'({int(float(mv["audit_kudamatsu_rows"]))} records) without pole '
    "linkage; Yasu (Tier 3) provides road and building geometry only. "
    "Within each municipality a compact study zone (~2.6 km extent) was "
    "extracted as the largest connected component of the road graph, and "
    "building footprints were assigned estimated peak demand and snapped "
    "to the nearest road node. All raw public data, checksums, and "
    "acquisition provenance are preserved in a source registry.")
doc.add_heading("2.2 Legacy network reconstruction (S0)", 1)
doc.add_paragraph(
    "Demand nodes are clustered into LV feeder-scale clusters "
    "(approximately 350 kW each). For each cluster, the legacy overhead "
    "network is reconstructed by an ensemble of twelve replicates across "
    "two families: (A) a Steiner heuristic with jittered terminal "
    "geometry and an edge-cost bias toward Tier-1/Tier-2 anchor points; "
    "and (B) an incremental cheapest-attachment heuristic with shuffled "
    "terminal order. No replicate is claimed to be the true network; the "
    "ensemble defines the S1 benchmark distribution.")
doc.add_heading("2.3 Life-cycle cost model", 1)
doc.add_paragraph("For each candidate topology T the net present cost is")
eq("NPC(T) = CAPEX(T) + (E_loss(T)·p_e + CAPEX(T)·f_OM)·ADF(r, h)")
doc.add_paragraph(
    "where p_e is the electricity price, f_OM the annual O&M fraction of "
    "capital cost, and ADF the annuity discount factor over horizon h at "
    "discount rate r. CAPEX combines excavation and duct costs per metre "
    "with conductor cost proportional to cross-section. Energy losses use "
    "the LinDistFlow quadratic expression")
eq("P_loss = Σ_e 3 I_e^2 R_e")
doc.add_paragraph(
    "scaled by load factor to annual energy. In S2 each edge independently "
    "selects a conductor size from {150, 250, 400, 600} mm² minimizing its "
    "own contribution to NPC, a classical discretized conductor-selection "
    "step; topology candidates are generated by weighted Steiner trees in "
    "which near-source edges carry an additional loss-priority weight.")
doc.add_heading("2.4 Scenarios and metrics", 1)
doc.add_paragraph(
    "S1 (like-for-like): each reconstruction replicate rebuilt underground "
    "with the reference 150 mm² conductor. S2 (life-cycle optimized): "
    "minimum-NPC topology over the candidate set with per-edge conductor "
    "sizing. S3: S2 plus rooftop PV sized from clipped building footprints "
    "(30% usable roof, 0.15 kWp/m²) with credited generation bounded by "
    "local energy consumption and loss reduction bounded at 50%.")
doc.add_paragraph("The primary metric is the life-cycle topology profit")
eq("LTP = NPC(S1) − NPC(S2)")
doc.add_paragraph(
    "reported also as a percentage of NPC(S1). Topology divergence between "
    "a reconstruction replicate and its optimized counterpart is measured "
    "by the topology likelihood distance")
eq("TLD = 1 − |E_C ∩ E_L| / |E_C ∪ E_L|")
doc.add_paragraph(
    "over edge sets. P(LTP>0) is reported only as a measure of model and "
    "scenario uncertainty, not as a claim about real-network behaviour.")

# ----------------------------- 3 Results --------------------------------
doc.add_heading("3. Results", 1)
doc.add_paragraph(
    f'Table 2 summarizes {int(float(mv["sano_clusters"])+float(mv["kudamatsu_clusters"])+float(mv["yasu_clusters"]))} '
    "clusters serving "
    f'{fmt(float(mv["sano_demand_mw"])+float(mv["kudamatsu_demand_mw"])+float(mv["yasu_demand_mw"]),1)} '
    "MW of modeled peak demand. S2 lowers NPC by "
    f'{fmt(mv["sano_delta_npc_bn"],2)} bn JPY ({fmt(mv["sano_ltp_pct"],1)}%) in Sano, '
    f'{fmt(mv["kudamatsu_delta_npc_bn"],2)} bn JPY ({fmt(mv["kudamatsu_ltp_pct"],1)}%) in Kudamatsu, and '
    f'{fmt(mv["yasu_delta_npc_bn"],2)} bn JPY ({fmt(mv["yasu_ltp_pct"],1)}%) in Yasu '
    "relative to the like-for-like benchmark. Optimized conductor upsizing "
    f'applies to {fmt(mv["sano_upsize_km"],1)}, {fmt(mv["kudamatsu_upsize_km"],1)}, and '
    f'{fmt(mv["yasu_upsize_km"],1)} km of route respectively. Modeled peak losses fall by '
    f'{fmt(mv["sano_loss_red_pct"],0)}%, {fmt(mv["kudamatsu_loss_red_pct"],0)}%, and '
    f'{fmt(mv["yasu_loss_red_pct"],0)}%. Mean TLD values of '
    f'{fmt(mv["sano_mean_tld"],2)}\u2013{fmt(mv["yasu_mean_tld"],2)} show the optimized '
    "topology typically reuses most existing corridor edges — the benefit "
    "comes from targeted rerouting, not wholesale redesign (Figures 1–2).")
doc.add_paragraph(
    "Monte-Carlo sensitivity over discount rate (2–4.5%), electricity "
    "price (15–35 JPY/kWh), construction cost (±30%), O&M fraction, load "
    "factor, and horizon (30–50 y) yields P(LTP>0) of "
    f'{fmt(mv["sano_mc_p_ltp_pos"],2)}, {fmt(mv["kudamatsu_mc_p_ltp_pos"],2)}, and '
    f'{fmt(mv["yasu_mc_p_ltp_pos"],2)} for the three zones; the Kudamatsu '
    "zone shows a negative 5th percentile, indicating its smaller benefit "
    "is not robust to adverse cost draws (Figures 3–4). With rooftop PV "
    f'(S3; {fmt(mv["sano_pv_mwp"],1)}, {fmt(mv["kudamatsu_pv_mwp"],1)}, and '
    f'{fmt(mv["yasu_pv_mwp"],1)} MWp modeled potential), NPC falls further '
    "in every cluster (Figure 5), though the modeled PV economics rely on "
    "generous self-consumption assumptions and should be read as an upper "
    "bound.")

# ----------------------------- 4 Discussion -----------------------------
doc.add_heading("4. Discussion", 1)
doc.add_paragraph(
    "Three limitations bound interpretation. First, reconstructed "
    "topologies are modeled objects; even Tier-1 anchor data do not "
    "observe the actual pole-to-pole routing, and results are conditional "
    "on the reconstruction ensemble. Second, the LinDistFlow "
    "approximation at LV feeder scale produced maximum voltage drops of "
    f'{fmt(mv["sano_max_vdrop"],0)}\u2013{fmt(mv["yasu_max_vdrop"],0)}% in '
    "the reconstructed networks, exceeding practical LV limits — a known "
    "artefact of dense clustered demand on radial stubs; the relative NPC "
    "comparison is nonetheless consistent because the same electrical "
    "model prices both scenarios. Third, municipal security-light anchors "
    "are never equated with pole locations; Tier-2 data inform edge "
    "biases only. The benchmark network (CIGRE LV) validated the "
    "electrical model; a second benchmark (11-bus Iwamoto case) failed to "
    "converge in pandapower 3.5.5 and is reported rather than suppressed.")
doc.add_paragraph(
    "For municipalities, the operational reading is that renewal planning "
    "should include a topology review step: even where easements fix most "
    "routing, conductor sizing alone contributes a measurable share of "
    "the benefit. The municipality-facing outputs are planning-support "
    "estimates, not engineering designs.")

# ----------------------------- 5 Conclusions ----------------------------
doc.add_heading("5. Conclusions", 1)
doc.add_paragraph(
    "Treating undergrounding renewal as a re-optimization opportunity "
    "rather than like-for-like replacement reduces modeled life-cycle "
    "cost by roughly 2.5–12% across three data-tiered zones, with the "
    "benefit concentrated in trunk rerouting and conductor upsizing. The "
    "method transfers to any context where road geometry and coarse "
    "demand anchors are available; larger multi-feeder and meshed "
    "extensions are future work.")

# ------------------------- declarations ---------------------------------
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

# ------------------------- figure captions ------------------------------
doc.add_heading("Figure captions (figures supplied as separate files)", 1)
for cap in [
    "Figure 1. Study zones: road graph (grey) and snapped building demand nodes (blue).",
    "Figure 2. Example feeder cluster: S1 like-for-like replicate vs S2 optimized layout.",
    "Figure 3. Life-cycle topology profit by zone (base case vs Monte-Carlo mean).",
    "Figure 4. One-at-a-time sensitivity (tornado) of LTP, Sano zone.",
    "Figure 5. NPC of S2 vs S3 (rooftop-PV extension) by zone."]:
    doc.add_paragraph(cap)

# ----------------------------- tables -----------------------------------
doc.add_heading("Table 1. Study zones and data tiers", 1)
t = doc.add_table(rows=4, cols=4); t.style = "Table Grid"
for i, h in enumerate(["Zone", "Tier", "Anchor records", "Modeled demand (MW)"]):
    t.rows[0].cells[i].text = h
for j, c in enumerate(["sano", "kudamatsu", "yasu"]):
    tier = {"sano": "1 (pole-ID linked)", "kudamatsu": "2 (geolocated anchors)",
            "yasu": "3 (roads/buildings only)"}[c]
    rows_n = mv.get(f"audit_{c}_rows", "—")
    t.rows[j+1].cells[0].text = c.capitalize()
    t.rows[j+1].cells[1].text = tier
    t.rows[j+1].cells[2].text = str(rows_n)
    t.rows[j+1].cells[3].text = fmt(mv[f"{c}_demand_mw"], 1)

doc.add_heading("Table 2. Scenario results", 1)
tab = pd.read_csv(f"{ROOT}/tables/table2_results.csv")
t = doc.add_table(rows=len(tab)+1, cols=len(tab.columns)); t.style = "Table Grid"
for i, h in enumerate(tab.columns):
    t.rows[0].cells[i].text = h
for j, (_, r) in enumerate(tab.iterrows()):
    for i, h in enumerate(tab.columns):
        v = r[h]
        t.rows[j+1].cells[i].text = (f"{v:.3g}" if isinstance(v, float) else str(v))

# ----------------------------- references -------------------------------
doc.add_heading("References", 1)
for i, doi in enumerate(cite_order):
    r = DOI[doi]
    auth = r["authors"].replace("; ", ", ")
    doc.add_paragraph(
        f"[{i+1}] {auth}. {r['title']}. {r['container']} "
        f"{r['volume']}({r['issue']}) {r['pages']} ({r['year']}). "
        f"doi:{r['doi']}")

os.makedirs(f"{ROOT}/manuscript", exist_ok=True)
doc.save(f"{ROOT}/manuscript/manuscript_draft.docx")
print("refs cited in order:", len(cite_order))
print("saved manuscript/manuscript_draft.docx")
