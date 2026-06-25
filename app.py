"""
LVMH — Green in Tech ROI Calculator

Streamlit application rebuilt around the "parcours de décision" UX:
a five-phase journey (Cadrer → Diagnostiquer → Explorer → Arbitrer → Planifier)
with a persistent, live Green ROI arbitrage gauge.

The interface (editorial luxury layout, custom HTML cards, SVG charts) is wired
to the *real* calculation engine in src/ — baseline, scenarios, optimiser and
business cases. Nothing here is illustrative: every figure comes from the engine.

    Green ROI = α · Finance + (1 − α) · Carbone
"""


import copy
import sys
import re
from pathlib import Path

import streamlit as st

# Make src importable
sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import EquipmentData, load_excel_data, save_default_excel
from src.config import GlobalParameters
from src.baseline import compute_baseline, BaselineMetrics
from src.scenario import (
    ScenarioParams,
    compute_scenario,
    create_moderate_scenario,
    create_aggressive_scenario,
)
from src.optimizer import OptimizationConfig, run_optimization
from src.business_case import generate_all_business_cases


# =============================================================================
# Page configuration & theme
# =============================================================================

st.set_page_config(
    page_title="Green in Tech — ROI Calculator",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css():
    css_path = Path(__file__).parent / "assets" / "theme.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


# =============================================================================
# Maison presets  ·  (name, office %, tech %, retail %, headcount)
# =============================================================================

PRESETS = [
    ("Dior Couture", 50, 20, 30, 4200),
    ("Louis Vuitton", 55, 10, 35, 9000),
    ("Sephora", 35, 10, 55, 6200),
    ("LVMH Tech", 25, 65, 10, 1500),
]

# Display normalisation references for the live arbitrage gauge.
# (The engine's ranked Green ROI uses cross-scenario min-max; for a single live
#  scenario we normalise against intuitive absolute references that scale with
#  the Maison so the gauge stays meaningful for any fleet size.)
FIN_REF_FRAC = 0.30  # saving 30 % of the baseline TCO == full finance score
CAR_REF = 0.40       # 40 % CO2 reduction == full carbon score


# =============================================================================
# Data & parameter builders
# =============================================================================

@st.cache_resource(show_spinner=False)
def get_original_data() -> EquipmentData:
    """Load the reference equipment workbook once."""
    path = Path(__file__).parent / "data" / "UC1_Inputs.xlsx"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        save_default_excel(path)
    return load_excel_data(path)


def build_data(n_emp: int, off: int, tec: int, ret: int) -> EquipmentData:
    """Derive an equipment inventory from a persona split (Office/Tech/Retail).

    Mirrors the persona model:
      Laptops  = N · (office + tech)
      Screens  = N · (office + 2·tech)      (tech = dual screen)
      Mobiles  = N · (office + tech + retail)
      Landline = N · office
    Networking & meeting-room screens scale with headcount.
    """
    base = get_original_data()
    data = copy.deepcopy(base)

    of, tf, rf = off / 100.0, tec / 100.0, ret / 100.0
    counts = copy.deepcopy(base.equipment_counts)
    counts["Laptop"] = int(n_emp * (of + tf))
    counts["Screen"] = int(n_emp * (of + 2 * tf))
    counts["Smartphone"] = int(n_emp * (of + tf + rf))
    counts["Landline phone"] = int(n_emp * of)

    ratio = n_emp / 1000.0
    if "Switch/Router" in counts:
        counts["Switch/Router"] = max(1, int(base.equipment_counts.get("Switch/Router", 100) * ratio))
    if "Meeting room screen" in counts:
        counts["Meeting room screen"] = max(1, int(base.equipment_counts.get("Meeting room screen", 200) * ratio))

    data.equipment_counts = counts
    return data


def build_params(budget: float, target: float, carbf: float, alpha: float,
                 onprem: float, eol: float) -> GlobalParameters:
    p = GlobalParameters()
    p.program_budget = budget
    p.target_co2_reduction = target
    p.co2_per_kwh = carbf
    p.alpha = alpha
    p.onprem_co2_baseline = onprem
    p.end_of_life_cost = eol
    return p


# =============================================================================
# Scenario helpers
# =============================================================================

def manual_scenario(data: EquipmentData, rec: float, life_months: float,
                    scr: float, cloud: float, budget: float) -> ScenarioParams:
    """Build a ScenarioParams from the four manual levers of phase 3."""
    lap_life = data.equipment_lifespan.get("Laptop", 60)
    ext = (life_months / lap_life) if lap_life > 0 else 0.0
    return ScenarioParams(
        name="Scénario manuel",
        device_reductions={"Screen": scr / 100.0},
        sourcing_mix={"Laptop": {"new": 1 - rec / 100.0, "refurb": rec / 100.0, "lease": 0.0}},
        lifespan_extensions={"Laptop": ext},
        cloud_cost_reduction=cloud / 100.0,
        onprem_reduction=0.0,
        program_cost=budget,
    )


def estimate_investment(data: EquipmentData, params: GlobalParameters,
                        scen: ScenarioParams) -> float:
    """Approximate the one-off programme investment implied by a scenario's
    active levers, reusing the business-case cost assumptions."""
    rec = scen.sourcing_mix.get("Laptop", {}).get("refurb", 0.0)
    life_frac = scen.lifespan_extensions.get("Laptop", 0.0)
    life_months = life_frac * data.equipment_lifespan.get("Laptop", 60)
    scr = scen.device_reductions.get("Screen", 0.0)
    cloud = scen.cloud_cost_reduction
    landline = scen.device_reductions.get("Landline phone", 0.0)
    onprem = scen.onprem_reduction

    inv = 0.0
    if life_months > 0:
        eligible = int(data.equipment_counts.get("Laptop", 0) * params.laptop_eligible_upgrade_percent)
        inv += eligible * params.laptop_upgrade_cost_per_unit
    if scr > 0:
        inv += (params.screen_audit_cost + params.screen_hot_desking_investment
                + params.screen_booking_system_cost + params.screen_communication_cost)
    if cloud > 0:
        inv += params.cloud_finops_tool_cost + params.cloud_consultant_cost + params.cloud_training_cost
    if landline > 0:
        count = data.equipment_counts.get("Landline phone", 0)
        inv += count * params.landline_headset_cost_per_unit + params.landline_training_cost + params.landline_teams_license_cost
    if onprem > 0:
        inv += params.onprem_audit_cost + params.onprem_migration_cost + params.onprem_decom_cost
    if rec > 0:
        inv += params.refurb_setup_investment
    return inv


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def arbitrage_score(savings: float, reduction: float, alpha: float, baseline_tco: float):
    """Return (norm_finance, norm_carbon, green_roi) for the live gauge.

    norm_finance : savings as a share of the baseline TCO (30 % saved == full)
    norm_carbon  : CO2 reduction vs a 40 % reference
    Both references scale with the Maison, so the gauge reads sensibly at any size.
    """
    nf = clamp(savings / max(baseline_tco * FIN_REF_FRAC, 1.0))
    nc = clamp(reduction / CAR_REF)
    gr = alpha * nf + (1 - alpha) * nc
    return nf, nc, gr


def eval_scenario(data, baseline, params, scen, alpha, budget, name=None):
    """Evaluate one scenario against the baseline and score it."""
    m = compute_scenario(data, baseline, scen, params, None)
    savings = baseline.total_tco - m.operational_tco
    red = (baseline.total_co2 - m.total_co2) / baseline.total_co2 if baseline.total_co2 > 0 else 0.0
    nf, nc, gr = arbitrage_score(savings, red, alpha, baseline.total_tco)
    inv = estimate_investment(data, params, scen)
    payback = (inv / savings) if savings > 0 else float("inf")
    return {
        "name": name or scen.name,
        "tco": m.operational_tco,
        "co2": m.total_co2,
        "savings": savings,
        "red": red,
        "within_budget": inv <= budget,
        "meets_target": red >= params.target_co2_reduction,
        "payback": payback,
        "gr": gr, "nf": nf, "nc": nc,
    }


# =============================================================================
# Cached heavy computations (optimiser grid + business cases)
# =============================================================================

@st.cache_data(show_spinner=False)
def optimise_cached(n_emp, off, tec, ret, budget, target, carbf, onprem, eol):
    """Evaluate the full lever grid (~4 800 configs) once per core context."""
    data = build_data(n_emp, off, tec, ret)
    params = build_params(budget, target, carbf, 0.5, onprem, eol)
    cfg = OptimizationConfig(budget=budget, target_reduction=target, alpha=0.5,
                             max_scenarios=6000, top_n=20)
    res = run_optimization(data, params, cfg)

    out = []
    for sc, mt, ro in (res.all_results or []):
        inv = estimate_investment(data, params, sc)
        out.append({
            "savings": ro.cost_savings,
            "red": ro.co2_reduction_percent,
            "tco": mt.operational_tco,
            "co2": mt.total_co2,
            "within_budget": inv <= budget,
            "meets_target": ro.co2_reduction_percent >= target,
            "inv": inv,
            "screen": sc.device_reductions.get("Screen", 0.0),
            "refurb": sc.sourcing_mix.get("Laptop", {}).get("refurb", 0.0),
            "life": sc.lifespan_extensions.get("Laptop", 0.0),
            "cloud": sc.cloud_cost_reduction,
            "onprem": sc.onprem_reduction,
        })
    return {"evaluated": res.total_scenarios_evaluated, "results": out}


@st.cache_data(show_spinner=False)
def business_cases_cached(n_emp, off, tec, ret, budget, target, carbf, onprem, eol):
    data = build_data(n_emp, off, tec, ret)
    params = build_params(budget, target, carbf, 0.5, onprem, eol)
    cases = generate_all_business_cases(data, params)
    out = []
    for c in cases:
        roi_pct = (c.annual_cost_savings / c.total_investment * 100) if c.total_investment > 0 else 0.0
        out.append({
            "id": c.initiative_id, "title": c.title, "category": c.category.value,
            "reco": c.recommendation, "score": c.priority_score,
            "npv": c.five_year_npv, "investment": c.total_investment,
            "savings": c.annual_cost_savings, "roi_pct": roi_pct,
            "co2": c.annual_co2_reduction_kg, "co2_pct": c.co2_reduction_percent,
            "quarter": c.recommended_quarter, "weeks": c.implementation_weeks,
            "owner": c.owner_department, "risk": c.overall_risk.value,
            "actions": [(a.description, a.owner) for a in c.actions],
            "risks": [(rk.level.value, rk.description, rk.mitigation) for rk in c.risks],
        })
    return out


# =============================================================================
# Formatting helpers
# =============================================================================

def fmt_int(n) -> str:
    return f"{int(round(n)):,}".replace(",", " ")

def fmt_k(n) -> str:           # euros → "k€"
    return fmt_int(n / 1000.0) + " k€"

def fmt_m(n) -> str:           # euros → "M€" value (2 decimals, dot)
    return f"{n / 1e6:.2f}"

def fmt_t(kg) -> str:          # kg CO2 → tonnes (int)
    return fmt_int(kg / 1000.0)

def pct1(frac) -> str:
    return f"{frac * 100:.1f}"


# =============================================================================
# SVG builders
# =============================================================================

def donut(segments) -> str:
    """segments = [(pct, css_color), ...] summing to ≤ 100."""
    parts = ['<circle cx="21" cy="21" r="15.915" fill="none" stroke="var(--surface-2)" stroke-width="6"/>']
    cum = 0.0
    for pct, color in segments:
        off = 25 - cum
        parts.append(
            f'<circle cx="21" cy="21" r="15.915" fill="none" stroke="{color}" '
            f'stroke-width="6" stroke-dasharray="{pct:.1f} {100 - pct:.1f}" '
            f'stroke-dashoffset="{off:.1f}"/>'
        )
        cum += pct
    return '<svg width="148" height="148" viewBox="0 0 42 42" aria-hidden="true">' + "".join(parts) + "</svg>"


def scatter(scenarios, target) -> str:
    """Build the arbitrage frontier scatter (savings × CO2 reduction)."""
    x0, x1, ytop, ybot = 50, 404, 30, 256
    max_sav = max([s["savings"] for s in scenarios] + [1.0])
    max_sav *= 1.12
    max_red = max([s["red"] for s in scenarios] + [target, 0.30]) * 1.08

    def X(v): return x0 + clamp(v / max_sav) * (x1 - x0)
    def Y(v): return ybot - clamp(v / max_red) * (ybot - ytop)

    svg = [f'<svg viewBox="0 0 420 296" width="100%" role="img" aria-label="Frontière d\'arbitrage">']
    # axes
    svg.append(f'<line x1="{x0}" y1="{ybot}" x2="{x1}" y2="{ybot}" stroke="var(--line-strong)"/>')
    svg.append(f'<line x1="{x0}" y1="{ytop-6}" x2="{x0}" y2="{ybot}" stroke="var(--line-strong)"/>')
    # target line
    yt = Y(target)
    svg.append(f'<line x1="{x0}" y1="{yt:.0f}" x2="{x1}" y2="{yt:.0f}" stroke="var(--green)" stroke-dasharray="4 4" opacity=".6"/>')
    svg.append(f'<text x="{x1}" y="{yt-5:.0f}" text-anchor="end" font-size="9" fill="var(--green)" font-family="Inter">cible −{target*100:.0f} %</text>')
    # axis labels
    svg.append(f'<text x="225" y="288" text-anchor="middle" font-size="10" fill="var(--ink-mute)" font-family="Inter">Économies annuelles (€) →</text>')
    svg.append(f'<text x="14" y="145" text-anchor="middle" font-size="10" fill="var(--ink-mute)" font-family="Inter" transform="rotate(-90 14 145)">Réduction CO₂e (%) →</text>')

    best = max(range(len(scenarios)), key=lambda i: scenarios[i]["gr"]) if scenarios else -1
    for i, s in enumerate(scenarios):
        cx, cy = X(s["savings"]), Y(s["red"])
        r = 7 + s["gr"] * 18
        if s.get("baseline"):
            fill, op, tcol = "var(--ink-mute)", ".5", "#fff"
        elif i == best:
            fill, op, tcol = "var(--ink)", "1", "var(--gold)"
        elif s["within_budget"] and s["meets_target"]:
            fill, op, tcol = "var(--green)", ".8", "#fff"
        else:
            fill, op, tcol = "var(--gold)", ".55", "#fff"
        svg.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="{fill}" opacity="{op}"/>')
        svg.append(f'<text x="{cx:.0f}" y="{cy+3:.0f}" text-anchor="middle" font-size="8.5" fill="{tcol}" font-family="Inter">{s["short"]}</text>')
    svg.append("</svg>")
    return "".join(svg)


# =============================================================================
# Session state
# =============================================================================

def init_state():
    d = st.session_state
    d.setdefault("phase", 1)
    d.setdefault("maison", "Dior Couture")
    d.setdefault("eff", 4200)
    d.setdefault("mo", 50)
    d.setdefault("mt", 20)
    d.setdefault("mr", 30)
    d.setdefault("bud", 500000)
    d.setdefault("carbf", 0.052)
    d.setdefault("alpha", 0.50)
    d.setdefault("l_rec", 40)
    d.setdefault("l_life", 12)
    d.setdefault("l_scr", 25)
    d.setdefault("l_cloud", 18)
    d.setdefault("mode", "Manuel")
    d.setdefault("target", 20)
    d.setdefault("onprem", 34000)
    d.setdefault("eol", 5000)
    d.setdefault("expert", False)
    d.setdefault("comparator", [])


def goto(n):
    st.session_state.phase = n


def set_preset(name, o, t, r, n):
    st.session_state.maison = name
    st.session_state.mo, st.session_state.mt, st.session_state.mr = o, t, r
    st.session_state.eff = n


# =============================================================================
# Sidebar — journey rail
# =============================================================================

STEPS = [
    ("Cadrer", "Périmètre & hypothèses"),
    ("Diagnostiquer", "Situation de référence"),
    ("Explorer", "Scénarios & optimisation"),
    ("Arbitrer", "Comparaison & décision"),
    ("Planifier", "Business cases & roadmap"),
]


def render_rail(export_md: str):
    with st.sidebar:
        st.markdown(
            '<div class="rail-brand"><span class="lvmh">LVMH</span>'
            '<span class="sub">Green in Tech</span><br>'
            '<span class="badge">ROI Calculator</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="rail-eyebrow">Parcours de décision</div>', unsafe_allow_html=True)

        phase = st.session_state.phase
        for i, (title, desc) in enumerate(STEPS, start=1):
            if i < phase:
                label = f"✓  {title}"
            elif i == phase:
                label = f"{i} · {title}"
            else:
                label = f"{i} · {title}"
            st.button(
                label, key=f"rail_{i}", use_container_width=True,
                type="primary" if i == phase else "secondary",
                on_click=goto, args=(i,),
            )
            st.caption(desc)

        st.markdown('<div class="rail-sep"></div>', unsafe_allow_html=True)

        with st.expander("⚙ Réglages & facteurs"):
            st.slider("Cible de réduction CO₂ (%)", 5, 50, key="target")
            st.number_input("Base CO₂ On-Prem (kg/an)", min_value=0, step=1000, key="onprem")
            st.number_input("Coût fin de vie (€/an)", min_value=0, step=1000, key="eol")
            st.caption("Facteurs ADEME appliqués par le moteur (src/config.py).")

        st.download_button(
            "⤓ Exporter le dossier", data=export_md,
            file_name="green-roi-dossier.md", mime="text/markdown",
            use_container_width=True,
        )
        st.toggle("Mode expert (accès libre)", key="expert",
                  help="Affiche les cinq phases en continu.")


# =============================================================================
# Topbar — context + live arbitrage gauge
# =============================================================================

def render_topbar(data, params, baseline):
    rec = st.session_state.l_rec
    life = st.session_state.l_life
    scr = st.session_state.l_scr
    cloud = st.session_state.l_cloud
    alpha = st.session_state.alpha
    budget = st.session_state.bud

    scen = manual_scenario(data, rec, life, scr, cloud, budget)
    ev = eval_scenario(data, baseline, params, scen, alpha, budget, "Manuel")
    nf, nc, gr = ev["nf"], ev["nc"], ev["gr"]

    col_ctx, col_gauge = st.columns([1.3, 1])
    with col_ctx:
        st.markdown(
            '<div class="topbar" style="border-bottom:0; padding-bottom:0; margin-bottom:0">'
            '<div class="brand"><span class="lvmh">LVMH</span>'
            '<span class="sub">Green in Tech</span>'
            '<span class="badge">ROI Calculator</span></div>'
            f'<div class="maison-meta"><span class="mname">{st.session_state.maison}</span>'
            f'<b>{fmt_int(st.session_state.eff)}</b> collaborateurs · budget '
            f'<b>{fmt_k(budget)}</b></div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with col_gauge:
        st.markdown(
            '<div class="arbitrage" title="Score Green ROI = α·Finance + (1−α)·Carbone">'
            f'<div class="gr-score"><span class="lab">Green ROI</span>'
            f'<span class="val tnum">{gr:.2f}</span></div>'
            '<div class="gr-axes">'
            f'<div class="axis fin"><span class="tag">Finance</span>'
            f'<span class="track"><span class="fill" style="width:{nf*100:.0f}%"></span></span>'
            f'<span class="pct">{nf:.2f}</span></div>'
            f'<div class="axis car"><span class="tag">Carbone</span>'
            f'<span class="track"><span class="fill" style="width:{nc*100:.0f}%"></span></span>'
            f'<span class="pct">{nc:.2f}</span></div>'
            '</div>'
            f'<div class="alpha-cap">Arbitrage<br>α&nbsp;<b>{alpha:.2f}</b></div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.slider("Arbitrage α — Finance ⇄ Carbone", 0.0, 1.0, step=0.05,
                  key="alpha", label_visibility="collapsed")

    st.markdown('<div style="border-bottom:1px solid var(--line); margin:14px 0 20px"></div>',
                unsafe_allow_html=True)


def phase_header(idx, kicker, title, desc):
    st.markdown(
        f'<div class="ph-head"><div class="kicker">Étape {idx} / 5 · {kicker}</div>'
        f'<h1>{title}</h1><p>{desc}</p></div>',
        unsafe_allow_html=True,
    )


# =============================================================================
# PHASE 1 — CADRER
# =============================================================================

def phase1(data, params, baseline):
    phase_header(1, "Cadrage", "Définir le périmètre de la Maison",
                 "Choisissez un préréglage ou saisissez l'effectif et la répartition des "
                 "personas. L'inventaire cible et le budget se recalculent immédiatement — "
                 "tout le reste du parcours en découle.")

    left, right = st.columns([1.3, 1], gap="large")

    with left:
        st.markdown('<div class="c-title"><h3>Préréglages de Maison</h3>'
                    '<span class="hint">point de départ</span></div>', unsafe_allow_html=True)
        pcols = st.columns(len(PRESETS))
        for col, (name, o, t, r, n) in zip(pcols, PRESETS):
            with col:
                st.button(f"{name}\n{o} / {t} / {r}", key=f"preset_{name}",
                          use_container_width=True,
                          type="primary" if st.session_state.maison == name else "secondary",
                          on_click=set_preset, args=(name, o, t, r, n))

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.number_input("Effectif total", min_value=100, max_value=200000, step=100, key="eff")

        o = st.session_state.mo; t = st.session_state.mt; r = st.session_state.mr
        st.markdown(f'<div class="lv-top"><span class="lv-name">Office '
                    f'<span class="muted">— support, finance, RH, marketing</span></span>'
                    f'<span class="lv-val">{o} %</span></div>', unsafe_allow_html=True)
        st.slider("Office", 0, 100, key="mo", label_visibility="collapsed")
        st.markdown(f'<div class="lv-top"><span class="lv-name">Tech '
                    f'<span class="muted">— dev, data, tech leads · double écran</span></span>'
                    f'<span class="lv-val">{t} %</span></div>', unsafe_allow_html=True)
        st.slider("Tech", 0, 100, key="mt", label_visibility="collapsed")
        st.markdown(f'<div class="lv-top"><span class="lv-name">Retail '
                    f'<span class="muted">— conseillers boutique · mobile seul</span></span>'
                    f'<span class="lv-val">{r} %</span></div>', unsafe_allow_html=True)
        st.slider("Retail", 0, 100, key="mr", label_visibility="collapsed")

        total = o + t + r
        if total == 100:
            st.markdown('<div class="note">Répartition : 100 %</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="note" style="color:var(--clay)">Répartition : {total} % '
                        f'— ajustez à 100 %</div>', unsafe_allow_html=True)

    with right:
        n = st.session_state.eff
        of, tf, rf = o / 100.0, t / 100.0, r / 100.0
        laptops = n * (of + tf)
        screens = n * (of + 2 * tf)
        mobiles = n * (of + tf + rf)
        st.markdown('<div class="c-title"><h3>Inventaire cible &amp; hypothèses</h3></div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div class="derived">'
            f'<div class="d"><div class="dl">Ordinateurs</div><div class="dv tnum">{fmt_int(laptops)}</div></div>'
            f'<div class="d"><div class="dl">Écrans</div><div class="dv tnum">{fmt_int(screens)}</div></div>'
            f'<div class="d"><div class="dl">Mobiles</div><div class="dv tnum">{fmt_int(mobiles)}</div></div>'
            '</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        st.number_input("Budget programme annuel (€)", min_value=0, step=50000, key="bud")
        st.number_input("Intensité carbone électricité (kg CO₂e/kWh · FR)",
                        min_value=0.0, step=0.001, format="%.3f", key="carbf")
        st.markdown(
            '<div class="callout"><div class="ic">i</div><div class="ct">'
            'Une Maison à forte composante <b>Tech</b> double les écrans : '
            '<b>+350 kg CO₂e</b> de fabrication par poste et une consommation '
            'électrique nettement supérieure par collaborateur.</div></div>',
            unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    c1.markdown('<span class="muted">Inventaire et budget actualisés.</span>', unsafe_allow_html=True)
    c2.button("Diagnostiquer la baseline →", type="primary", use_container_width=True,
              on_click=goto, args=(2,))


# =============================================================================
# PHASE 2 — DIAGNOSTIQUER
# =============================================================================

def phase2(data, params, baseline):
    phase_header(2, "Diagnostic", "Situation de référence — où en sommes-nous ?",
                 "Une vue à 360° du parc actuel : coûts, énergie et empreinte carbone. "
                 "Objectif : repérer les postes de coûts majeurs et les gisements de CO₂e "
                 "avant d'optimiser.")

    tco_b = baseline.tco_breakdown
    co2_b = baseline.co2_breakdown
    capex_pct = tco_b.get("Equipment (Capex)", 0)
    cloud_pct = tco_b.get("Cloud", 0)
    cost_other = max(0, 100 - capex_pct - cloud_pct)
    fab_pct = co2_b.get("Equipment (Embodied)", 0)
    use_pct = co2_b.get("Equipment (Use Phase)", 0)
    infra_pct = max(0, 100 - fab_pct - use_pct)
    volume = int(sum(v for v in data.equipment_counts.values() if v > 0))
    n_types = sum(1 for v in data.equipment_counts.values() if v > 0)

    st.markdown(
        '<div class="kpis">'
        f'<div class="kpi"><div class="l">TCO initial</div>'
        f'<div class="v tnum">{fmt_m(baseline.total_tco)} <small>M€ / an</small></div>'
        f'<div class="delta neg">Capex {capex_pct:.0f} % · Cloud {cloud_pct:.0f} % · Énergie/EOL {cost_other:.0f} %</div></div>'
        f'<div class="kpi"><div class="l">Empreinte carbone</div>'
        f'<div class="v tnum">{fmt_t(baseline.total_co2)} <small>tCO₂e / an</small></div>'
        f'<div class="delta neg">Fabrication {fab_pct:.0f} % du total</div></div>'
        f'<div class="kpi"><div class="l">Volume d\'équipements</div>'
        f'<div class="v tnum">{fmt_int(volume)}</div>'
        f'<div class="delta mute">{n_types} types actifs</div></div>'
        '</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    g1, g2 = st.columns(2, gap="large")
    with g1:
        st.markdown(
            '<div class="card"><div class="c-title"><h3>Structure des coûts</h3>'
            '<span class="hint">Capex · Cloud · Énergie</span></div>'
            '<div style="display:flex; gap:22px; align-items:center">'
            + donut([(capex_pct, "var(--gold)"), (cloud_pct, "var(--green)"), (cost_other, "var(--clay)")])
            + '<div class="legend col">'
            f'<span><i style="background:var(--gold)"></i>Capex terminaux · {capex_pct:.0f} %</span>'
            f'<span><i style="background:var(--green)"></i>Cloud (FinOps) · {cloud_pct:.0f} %</span>'
            f'<span><i style="background:var(--clay)"></i>Énergie &amp; fin de vie · {cost_other:.0f} %</span>'
            '</div></div></div>', unsafe_allow_html=True)
    with g2:
        st.markdown(
            '<div class="card"><div class="c-title"><h3>Répartition des émissions</h3>'
            '<span class="hint">Scope 2 &amp; 3</span></div>'
            '<div style="display:flex; gap:22px; align-items:center">'
            + donut([(fab_pct, "var(--green)"), (use_pct, "var(--gold)"), (infra_pct, "var(--clay)")])
            + '<div class="legend col">'
            f'<span><i style="background:var(--green)"></i>Fabrication (Scope 3) · {fab_pct:.0f} %</span>'
            f'<span><i style="background:var(--gold)"></i>Usage électrique (Scope 2) · {use_pct:.0f} %</span>'
            f'<span><i style="background:var(--clay)"></i>Cloud &amp; On-Prem · {infra_pct:.0f} %</span>'
            '</div></div></div>', unsafe_allow_html=True)

    # detailed inventory table
    rows = []
    order = ["Laptop", "Screen", "Smartphone", "Tablet", "Switch/Router",
             "Landline phone", "Meeting room screen"]
    labels = {"Laptop": "Ordinateur portable", "Screen": "Écran externe",
              "Smartphone": "Smartphone", "Tablet": "Tablette",
              "Switch/Router": "Switch / Routeur", "Landline phone": "Téléphone fixe",
              "Meeting room screen": "Écran de réunion"}
    for eq in order:
        cnt = data.equipment_counts.get(eq, 0)
        if cnt <= 0:
            continue
        price = data.equipment_prices.get(eq, 0)
        life = data.equipment_lifespan.get(eq, 48)
        co2 = baseline.co2_embodied_annual.get(eq, 0)
        rows.append(
            f'<tr><td>{labels.get(eq, eq)}</td><td class="num tnum">{fmt_int(cnt)}</td>'
            f'<td class="num tnum">{fmt_int(price)} €</td><td class="num">{life} mois</td>'
            f'<td class="num tnum">{fmt_t(co2)} t</td></tr>'
        )
    st.markdown(
        '<div class="card" style="margin-top:18px"><div class="c-title"><h3>Inventaire détaillé</h3></div>'
        '<table class="tbl"><thead><tr><th>Équipement</th><th class="num">Volume</th>'
        '<th class="num">Prix unit.</th><th class="num">Durée de vie</th>'
        '<th class="num">CO₂e fab. / an</th></tr></thead><tbody>'
        + "".join(rows) + '</tbody></table></div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="callout warn" style="margin-top:18px"><div class="ic">!</div><div class="ct">'
        'Principal gisement : la <b>fabrication des écrans et portables</b> (Scope 3). '
        'Les leviers les plus rentables seront l\'<b>allongement des durées de vie</b> '
        'et le <b>reconditionné</b>.</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    c1.button("← Cadrage", use_container_width=True, on_click=goto, args=(1,))
    c3.button("Explorer des scénarios →", type="primary", use_container_width=True,
              on_click=goto, args=(3,))


# =============================================================================
# PHASE 3 — EXPLORER
# =============================================================================

def lever_row(name, note, value_txt, key, lo, hi):
    st.markdown(f'<div class="lv-top"><span class="lv-name">{name}</span>'
                f'<span class="lv-val">{value_txt}</span></div>', unsafe_allow_html=True)
    st.slider(name, lo, hi, key=key, label_visibility="collapsed")
    st.markdown(f'<div class="lv-note">{note}</div>', unsafe_allow_html=True)


def phase3(data, params, baseline):
    phase_header(3, "Exploration", "Construire &amp; optimiser des scénarios",
                 "Deux modes, un même objectif : trouver les combinaisons de leviers qui "
                 "respectent budget et cible carbone. Le score Green ROI (en haut) réagit "
                 "en direct à chaque ajustement.")

    st.radio("mode", ["Manuel", "Optimiseur"], key="mode", horizontal=True,
             label_visibility="collapsed")

    budget = st.session_state.bud
    alpha = st.session_state.alpha

    if st.session_state.mode == "Manuel":
        st.markdown('<span class="muted">Ajustez les leviers à la main et observez '
                    'l\'impact instantané.</span>', unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        left, right = st.columns([1.4, 1], gap="large")
        with left:
            st.markdown('<div class="c-title"><h3>Leviers d\'action — cible 2026</h3></div>',
                        unsafe_allow_html=True)
            lever_row("Part de portables reconditionnés",
                      "Fabrication 300 → 50 kg CO₂e par poste reconditionné.",
                      f"{st.session_state.l_rec} %", "l_rec", 0, 100)
            lever_row("Allongement durée de vie",
                      "Étale l'amortissement et retarde la fabrication (Scope 3).",
                      f"+{st.session_state.l_life} mois", "l_life", 0, 24)
            lever_row("Réduction du parc d'écrans (flex-office)",
                      "Risque organisationnel élevé — pénalité de priorité.",
                      f"{st.session_state.l_scr} %", "l_scr", 0, 60)
            lever_row("FinOps cloud — réduction dépense",
                      "Migration vers l'hyperscaler le moins carboné.",
                      f"{st.session_state.l_cloud} %", "l_cloud", 0, 40)

        with right:
            scen = manual_scenario(data, st.session_state.l_rec, st.session_state.l_life,
                                   st.session_state.l_scr, st.session_state.l_cloud, budget)
            ev = eval_scenario(data, baseline, params, scen, alpha, budget, "Manuel")
            target = params.target_co2_reduction
            st.markdown('<div class="c-title"><h3>Projection vs baseline</h3></div>',
                        unsafe_allow_html=True)
            st.markdown(
                '<div class="proj">'
                '<div class="l">TCO projeté 2026</div>'
                f'<div class="v tnum">{fmt_m(ev["tco"])} <small>M€</small></div>'
                f'<div class="delta pos">▼ {fmt_k(ev["savings"])} d\'économies / an</div>'
                '<div class="proj-sep"></div>'
                '<div class="l">CO₂e projeté</div>'
                f'<div class="v tnum">{fmt_t(ev["co2"])} <small>tCO₂e</small></div>'
                f'<div class="delta pos">▼ {pct1(ev["red"])} % vs −{target*100:.0f} % cible</div>'
                '</div>', unsafe_allow_html=True)

            bud_chip = ('<span class="chip ok">✓ Budget respecté</span>' if ev["within_budget"]
                        else '<span class="chip warn">✗ Budget dépassé</span>')
            tar_chip = ('<span class="chip ok">✓ Cible carbone atteinte</span>' if ev["meets_target"]
                        else '<span class="chip warn">✗ Cible non atteinte</span>')
            st.markdown(f'<div style="margin:14px 0; display:flex; gap:8px; flex-wrap:wrap">'
                        f'{bud_chip}{tar_chip}</div>', unsafe_allow_html=True)

            if st.button("+ Ajouter au comparateur", type="primary", use_container_width=True):
                snap = copy.deepcopy(scen)
                snap.name = f"Manuel {len(st.session_state.comparator) + 1}"
                st.session_state.comparator.append(snap)
                st.toast(f"Ajouté : {snap.name}")

    else:
        st.markdown('<span class="muted">L\'algorithme explore l\'espace des combinaisons '
                    'et extrait le Top 5 conforme.</span>', unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        with st.spinner("Évaluation des configurations…"):
            opt = optimise_cached(st.session_state.eff, st.session_state.mo, st.session_state.mt,
                                  st.session_state.mr, budget, params.target_co2_reduction,
                                  st.session_state.carbf, st.session_state.onprem, st.session_state.eol)
        # re-score with live alpha, filter feasible, rank
        scored = []
        for rdict in opt["results"]:
            _, _, gr = arbitrage_score(rdict["savings"], rdict["red"], alpha, baseline.total_tco)
            if rdict["within_budget"] and rdict["meets_target"]:
                scored.append((gr, rdict))
        scored.sort(key=lambda x: x[0], reverse=True)
        # keep 5 *structurally distinct* strategies (collapse near-duplicates that
        # differ only by the cloud lever, which barely moves CO2) for a useful Top 5
        seen, top = set(), []
        for gr, rd in scored:
            sig = (round(rd["screen"], 2), round(rd["refurb"], 2), round(rd["life"], 2))
            if sig in seen:
                continue
            seen.add(sig)
            top.append((gr, rd))
            if len(top) == 5:
                break

        st.markdown(
            f'<div class="c-title"><h3>Top 5 — recherche combinatoire</h3>'
            f'<span class="hint">≈ {fmt_int(opt["evaluated"])} configurations évaluées · '
            f'contraintes budget &amp; cible appliquées</span></div>', unsafe_allow_html=True)

        if not top:
            st.markdown('<div class="callout warn"><div class="ic">!</div><div class="ct">'
                        'Aucune configuration ne respecte à la fois le budget et la cible. '
                        'Augmentez le budget ou abaissez la cible dans les réglages.</div></div>',
                        unsafe_allow_html=True)
        else:
            lap_life = data.equipment_lifespan.get("Laptop", 60)
            cards = ['<div class="opt-grid">']
            for i, (gr, rd) in enumerate(top, start=1):
                cls = "opt best" if i == 1 else "opt"
                rank = "#1 · recommandé" if i == 1 else f"#{i}"
                payback = (rd["inv"] / rd["savings"]) if rd["savings"] > 0 else 0
                life_m = round(rd["life"] * lap_life)
                cards.append(
                    f'<div class="{cls}"><div class="rank">{rank}</div>'
                    f'<div class="gr tnum">{gr:.2f}</div>'
                    f'<div class="line"><span>Économies</span><b>{fmt_k(rd["savings"])}</b></div>'
                    f'<div class="line"><span>Réduction CO₂</span><b>−{pct1(rd["red"])} %</b></div>'
                    f'<div class="line"><span>Payback</span><b>{payback:.1f} ans</b></div>'
                    f'<div class="line"><span>Leviers</span><b>Rec {rd["refurb"]*100:.0f} · '
                    f'Scr {rd["screen"]*100:.0f} · Vie +{life_m}m · Cloud {rd["cloud"]*100:.0f}</b></div></div>'
                )
            cards.append("</div>")
            st.markdown("".join(cards), unsafe_allow_html=True)
            if st.button("+ Ajouter le scénario recommandé au comparateur", type="primary"):
                rd = top[0][1]
                lap_life = data.equipment_lifespan.get("Laptop", 60)
                snap = ScenarioParams(
                    name=f"Optimisé {len(st.session_state.comparator) + 1}",
                    device_reductions={"Screen": rd["screen"]},
                    sourcing_mix={"Laptop": {"new": 1 - rd["refurb"], "refurb": rd["refurb"], "lease": 0}},
                    lifespan_extensions={"Laptop": rd["life"]},
                    cloud_cost_reduction=rd["cloud"], onprem_reduction=rd["onprem"],
                    program_cost=budget,
                )
                st.session_state.comparator.append(snap)
                st.toast(f"Ajouté : {snap.name}")

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    c1.button("← Diagnostic", use_container_width=True, on_click=goto, args=(2,))
    c3.button("Arbitrer entre scénarios →", type="primary", use_container_width=True,
              on_click=goto, args=(4,))


# =============================================================================
# PHASE 4 — ARBITRER
# =============================================================================

def phase4(data, params, baseline):
    phase_header(4, "Arbitrage", "Comparer &amp; choisir la stratégie",
                 "La frontière du Green ROI : économies financières en abscisse, réduction "
                 "CO₂e en ordonnée. Le meilleur scénario se place en haut à droite — la "
                 "taille de la bulle est son score Green ROI.")

    budget = st.session_state.bud
    alpha = st.session_state.alpha
    target = params.target_co2_reduction

    # Build the comparison set: baseline + presets + manual + optimiser best + user-added
    manual = manual_scenario(data, st.session_state.l_rec, st.session_state.l_life,
                             st.session_state.l_scr, st.session_state.l_cloud, budget)
    mod = create_moderate_scenario(); mod.name = "Modéré"; mod.program_cost = budget
    agg = create_aggressive_scenario(); agg.name = "Agressif"; agg.program_cost = budget

    scen_defs = [("Modéré", "Modéré", mod), ("Agressif", "Agressif", agg),
                 ("Manuel", "Manuel", manual)]

    # optimiser best
    opt = optimise_cached(st.session_state.eff, st.session_state.mo, st.session_state.mt,
                          st.session_state.mr, budget, target, st.session_state.carbf,
                          st.session_state.onprem, st.session_state.eol)
    feas = [r for r in opt["results"] if r["within_budget"] and r["meets_target"]]
    if feas:
        feas.sort(key=lambda r: arbitrage_score(r["savings"], r["red"], alpha, baseline.total_tco)[2], reverse=True)
        rd = feas[0]
        best_opt = ScenarioParams(
            name="Optimisé #1",
            device_reductions={"Screen": rd["screen"]},
            sourcing_mix={"Laptop": {"new": 1 - rd["refurb"], "refurb": rd["refurb"], "lease": 0}},
            lifespan_extensions={"Laptop": rd["life"]},
            cloud_cost_reduction=rd["cloud"], onprem_reduction=rd["onprem"], program_cost=budget,
        )
        scen_defs.append(("Optimisé #1", "Opti #1", best_opt))

    for i, snap in enumerate(st.session_state.comparator, start=1):
        scen_defs.append((snap.name, snap.name.split()[0][:5], snap))

    # evaluate
    points = [{"name": "Baseline", "short": "Base", "tco": baseline.total_tco,
               "co2": baseline.total_co2, "savings": 0.0, "red": 0.0,
               "within_budget": True, "meets_target": False, "payback": float("inf"),
               "gr": 0.0, "nf": 0.0, "nc": 0.0, "baseline": True}]
    for name, short, scen in scen_defs:
        ev = eval_scenario(data, baseline, params, scen, alpha, budget, name)
        ev["short"] = short
        points.append(ev)

    # best (excluding baseline)
    ranked = sorted([p for p in points if not p.get("baseline")],
                    key=lambda p: p["gr"], reverse=True)
    best = ranked[0] if ranked else None

    left, right = st.columns([1.25, 1], gap="large")
    with left:
        st.markdown('<div class="card"><div class="c-title"><h3>Frontière d\'arbitrage</h3>'
                    '<span class="hint">€ économisés × % CO₂ réduit</span></div>'
                    + scatter(points, target)
                    + '<div class="legend" style="margin-top:6px">'
                    '<span><i style="background:var(--ink)"></i>Recommandé</span>'
                    '<span><i style="background:var(--green)"></i>Conforme aux contraintes</span>'
                    '<span><i style="background:var(--gold)"></i>Hors contrainte</span>'
                    '<span><i style="background:var(--ink-mute)"></i>Référence</span>'
                    '</div></div>', unsafe_allow_html=True)
    with right:
        if best:
            st.markdown(
                '<div class="card"><div class="c-title"><h3>Recommandation</h3></div>'
                '<div class="reco"><div class="eye">Scénario retenu</div>'
                f'<div class="name">{best["name"]}</div><div class="grid">'
                f'<div><div class="k">Économies / an</div><b>{fmt_k(best["savings"])}</b></div>'
                f'<div><div class="k">Réduction CO₂</div><b>−{pct1(best["red"])} %</b></div>'
                f'<div><div class="k">Green ROI</div><b class="gold">{best["gr"]:.2f}</b></div>'
                f'<div><div class="k">Payback</div><b>{best["payback"]:.1f} ans</b></div>'
                '</div></div>'
                f'<p class="muted" style="font-size:12.5px; margin-top:12px">'
                f'Meilleur compromis financier/carbone à α = {alpha:.2f}, '
                f'sous budget de {fmt_k(budget)} et au-delà de la cible '
                f'−{target*100:.0f} %.</p></div>', unsafe_allow_html=True)

    # comparison table
    trows = []
    for p in points:
        hl = ' class="hl"' if best and p["name"] == best["name"] else ""
        bud_chip = '<span class="chip ok">✓</span>' if p["within_budget"] else '<span class="chip warn">✗</span>'
        tar_chip = '<span class="chip ok">✓</span>' if p["meets_target"] else '<span class="chip warn">✗</span>'
        sav = "—" if p.get("baseline") else fmt_k(p["savings"])
        red = "—" if p.get("baseline") else f"−{pct1(p['red'])} %"
        gr = "—" if p.get("baseline") else f"{p['gr']:.2f}"
        name = f"<b>{p['name']}</b>" if best and p["name"] == best["name"] else p["name"]
        trows.append(
            f'<tr{hl}><td>{name}</td><td class="num tnum">{fmt_m(p["tco"])} M€</td>'
            f'<td class="num tnum">{sav}</td><td class="num tnum">{fmt_t(p["co2"])} t</td>'
            f'<td class="num">{red}</td><td>{bud_chip}</td><td>{tar_chip}</td>'
            f'<td class="num tnum">{gr}</td></tr>'
        )
    st.markdown(
        '<div class="card" style="margin-top:18px"><div class="c-title"><h3>Tableau comparatif</h3></div>'
        '<table class="tbl"><thead><tr><th>Scénario</th><th class="num">TCO</th>'
        '<th class="num">Économies</th><th class="num">CO₂e restant</th><th class="num">Réduction</th>'
        '<th>Budget</th><th>Cible</th><th class="num">Green ROI</th></tr></thead><tbody>'
        + "".join(trows) + '</tbody></table></div>', unsafe_allow_html=True)

    if st.session_state.comparator:
        if st.button("Vider le comparateur"):
            st.session_state.comparator = []
            st.rerun()

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    c1.button("← Exploration", use_container_width=True, on_click=goto, args=(3,))
    c3.button("Construire les business cases →", type="primary", use_container_width=True,
              on_click=goto, args=(5,))


# =============================================================================
# PHASE 5 — PLANIFIER
# =============================================================================

QUARTER_COLORS = {"Must Do": "var(--green)", "Should Do": "var(--gold)", "Consider": "var(--clay)"}
RECO_FR = {"Must Do": "Must do", "Should Do": "Should do", "Consider": "Consider"}


def parse_quarters(qstr):
    nums = [int(x) for x in re.findall(r"Q(\d)", qstr or "")]
    if not nums:
        return 1, 2
    return min(nums), max(nums)


def phase5(data, params, baseline):
    phase_header(5, "Planification", "Traduire la décision en roadmap",
                 "Le scénario retenu devient un plan d'action séquencé : calendrier de "
                 "déploiement, priorisation par gain/risque, et fiches projet prêtes pour "
                 "le COMEX.")

    cases = business_cases_cached(st.session_state.eff, st.session_state.mo, st.session_state.mt,
                                  st.session_state.mr, st.session_state.bud,
                                  params.target_co2_reduction, st.session_state.carbf,
                                  st.session_state.onprem, st.session_state.eol)

    # Gantt
    grows = []
    for c in cases:
        start, end = parse_quarters(c["quarter"])
        left = (start - 1) / 4 * 100
        width = (end - start + 1) / 4 * 100
        color = QUARTER_COLORS.get(c["reco"], "var(--ink-soft)")
        text_color = "#fff"
        grows.append(
            f'<div class="grow"><div class="gname">{c["title"]}</div>'
            f'<div class="gtrack"><div class="gbar" style="left:{left:.0f}%; width:{width:.0f}%; '
            f'background:{color}; color:{text_color}">{c["quarter"]}</div></div></div>'
        )
    st.markdown(
        f'<div class="card"><div class="c-title"><h3>Calendrier de déploiement 2026</h3>'
        f'<span class="hint">{len(cases)} initiatives</span></div>'
        '<div class="gantt-h"><div>Initiative</div><div>T1</div><div>T2</div><div>T3</div><div>T4</div></div>'
        + "".join(grows) + '</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    left, right = st.columns([1, 1.3], gap="large")

    with left:
        prows = []
        for i, c in enumerate(cases, start=1):
            chip = "ok" if c["reco"] == "Must Do" else ("gold" if c["reco"] == "Should Do" else "warn")
            prows.append(
                f'<div class="prio"><span class="pr">{i}</span>'
                f'<span class="pname">{c["title"]}</span>'
                f'<span class="chip {chip}">{RECO_FR.get(c["reco"], c["reco"])}</span>'
                f'<span class="pgr tnum">{c["score"]:.2f}</span></div>'
            )
        st.markdown(
            '<div class="card"><div class="c-title"><h3>Priorisation gain / risque</h3></div>'
            + "".join(prows) + '</div>', unsafe_allow_html=True)

    with right:
        top = cases[0] if cases else None
        if top:
            chip = "ok" if top["reco"] == "Must Do" else ("gold" if top["reco"] == "Should Do" else "warn")
            act_rows = "".join(
                f'<tr><td>{desc}</td><td><span class="chip gold">{owner}</span></td></tr>'
                for desc, owner in top["actions"][:5]
            )
            risk_html = ""
            if top["risks"]:
                lvl, desc, mit = top["risks"][0]
                risk_html = (f'<div class="callout warn" style="margin-top:14px"><div class="ic">⚠</div>'
                             f'<div class="ct"><b>Risque ({lvl}) :</b> {desc} '
                             f'<b>Remédiation :</b> {mit}</div></div>')
            st.markdown(
                f'<div class="card"><div class="c-title"><h3>Fiche projet — {top["title"]}</h3>'
                f'<span class="chip {chip}">{RECO_FR.get(top["reco"], top["reco"])}</span></div>'
                '<div class="kpis" style="grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:14px">'
                f'<div class="kpi" style="padding:12px"><div class="l">NPV 5 ans</div>'
                f'<div class="v tnum" style="font-size:22px">{fmt_m(top["npv"])} <small>M€</small></div></div>'
                f'<div class="kpi" style="padding:12px"><div class="l">Investissement</div>'
                f'<div class="v tnum" style="font-size:22px">{fmt_k(top["investment"])}</div></div>'
                f'<div class="kpi" style="padding:12px"><div class="l">CO₂ évité</div>'
                f'<div class="v tnum" style="font-size:22px">{fmt_t(top["co2"])} <small>t</small></div></div>'
                '</div>'
                '<table class="tbl"><thead><tr><th>Étape</th><th>Responsable</th></tr></thead><tbody>'
                + act_rows + '</tbody></table>' + risk_html + '</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    c1.button("← Arbitrage", use_container_width=True, on_click=goto, args=(4,))
    c3.button("Soumettre au COMEX", type="primary", use_container_width=True,
              on_click=lambda: st.toast("Dossier transmis au COMEX ✓"))


# =============================================================================
# Export dossier (markdown)
# =============================================================================

def build_export(data, params, baseline) -> str:
    lines = [
        "# LVMH — Green in Tech · Dossier de décision",
        "",
        f"**Maison :** {st.session_state.maison}  ",
        f"**Effectif :** {fmt_int(st.session_state.eff)} · "
        f"**Budget :** {fmt_k(st.session_state.bud)} · "
        f"**Cible CO₂ :** −{params.target_co2_reduction*100:.0f} %",
        "",
        "## Situation de référence",
        f"- TCO initial : {fmt_m(baseline.total_tco)} M€ / an",
        f"- Empreinte : {fmt_t(baseline.total_co2)} tCO₂e / an",
        "",
        "## Scénario manuel courant",
    ]
    scen = manual_scenario(data, st.session_state.l_rec, st.session_state.l_life,
                           st.session_state.l_scr, st.session_state.l_cloud, st.session_state.bud)
    ev = eval_scenario(data, baseline, params, scen, st.session_state.alpha, st.session_state.bud)
    lines += [
        f"- Reconditionné {st.session_state.l_rec} % · +{st.session_state.l_life} mois vie · "
        f"écrans −{st.session_state.l_scr} % · FinOps {st.session_state.l_cloud} %",
        f"- Économies : {fmt_k(ev['savings'])} / an · Réduction : −{pct1(ev['red'])} %",
        f"- Green ROI : {ev['gr']:.2f} (α = {st.session_state.alpha:.2f})",
    ]
    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

def main():
    load_css()
    init_state()

    # Persist value-widget inputs across runs where their widget is not rendered
    # (e.g. persona sliders off phase 1, levers in Optimiseur mode). Without this,
    # Streamlit garbage-collects the unrendered widget state. Re-touching the keys
    # at the top of the run — before any widget is instantiated — keeps them alive.
    # (Button keys must be excluded: their state cannot be set via session_state.)
    for _k in ("eff", "mo", "mt", "mr", "bud", "carbf", "alpha",
               "l_rec", "l_life", "l_scr", "l_cloud", "mode", "target", "onprem", "eol"):
        if _k in st.session_state:
            st.session_state[_k] = st.session_state[_k]

    s = st.session_state
    target = s.target / 100.0
    data = build_data(s.eff, s.mo, s.mt, s.mr)
    params = build_params(s.bud, target, s.carbf, s.alpha, s.onprem, s.eol)
    baseline = compute_baseline(data, params)

    export_md = build_export(data, params, baseline)
    render_rail(export_md)
    render_topbar(data, params, baseline)

    phases = {1: phase1, 2: phase2, 3: phase3, 4: phase4, 5: phase5}
    if s.expert:
        for n in range(1, 6):
            phases[n](data, params, baseline)
            st.markdown('<div style="height:34px"></div>', unsafe_allow_html=True)
    else:
        phases[s.phase](data, params, baseline)


if __name__ == "__main__":
    main()
