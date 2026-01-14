"""
LVMH Green in Tech ROI Calculator

A comprehensive Streamlit application for calculating and optimizing
the ROI of LVMH's Green in Tech initiative, combining financial and
environmental metrics into a unified Green ROI score.

Model Assumptions:
- ADEME emission factors are placeholders and editable in the UI
- Optimization uses heuristic grid search (not exact solver)  
- Dell laptop contract pricing: 700€ new, 850€ refurbished (editable)
- Target: 20% CO₂ reduction by 2026
- Annual program budget: 500,000€
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import copy
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import (
    EquipmentData, 
    load_excel_data, 
    save_default_excel,
    create_default_excel_data,
)
from src.config import (
    ADEME_EMISSION_FACTORS,
    ELECTRICITY_CO2_PER_KWH,
    CLOUD_CO2_FACTORS,
    GlobalParameters,
    DEFAULT_PERSONAS,
    DEFAULT_INITIATIVES,
)
from src.baseline import compute_baseline, BaselineMetrics
from src.scenario import (
    ScenarioParams, 
    ScenarioMetrics,
    compute_scenario,
    create_default_scenario,
    create_moderate_scenario,
    create_aggressive_scenario,
)
from src.roi import compute_all_roi_metrics, ROIMetrics
from src.optimizer import (
    OptimizationConfig,
    run_optimization,
    compute_initiative_contributions,
    quick_rank_scenarios,
)
from src.business_case import (
    generate_all_business_cases,
    BusinessCase,
    RiskLevel,
)

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="LVMH Green in Tech ROI Calculator",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS
def load_css():
    css_path = Path(__file__).parent / "assets" / "theme.css"
    if css_path.exists():
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    # Additional professional styling
    st.markdown("""
    <style>
    /* Business case card styling */
    .business-case-card {
        background: linear-gradient(135deg, #FAFAF8 0%, #F5F0E6 100%);
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 16px;
        border-left: 4px solid #4A7C59;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .business-case-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }
    
    .business-case-title {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.25rem;
        color: #1A1A1A;
        margin: 0;
    }
    
    .category-badge {
        background: #1A1A1A;
        color: #F5F0E6;
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .action-item {
        display: flex;
        align-items: flex-start;
        padding: 12px 0;
        border-bottom: 1px solid rgba(0,0,0,0.08);
    }
    
    .action-number {
        background: #4A7C59;
        color: white;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        margin-right: 12px;
        flex-shrink: 0;
    }
    
    .action-content {
        flex: 1;
    }
    
    .action-desc {
        color: #1A1A1A;
        margin-bottom: 4px;
    }
    
    .action-meta {
        font-size: 0.8rem;
        color: #6D6D6D;
    }
    
    .risk-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    .risk-low { background: #E8F5E9; color: #2E7D32; }
    .risk-medium { background: #FFF3E0; color: #E65100; }
    .risk-high { background: #FFEBEE; color: #C62828; }
    
    .metric-highlight {
        font-size: 2rem;
        font-weight: 600;
        color: #4A7C59;
    }
    
    .recommendation-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 0.05em;
    }
    
    .rec-must-do { background: #4A7C59; color: white; }
    .rec-should-do { background: #C4A35A; color: #1A1A1A; }
    .rec-consider { background: #E8E0D5; color: #1A1A1A; }
    
    /* Metric card styling */
    .metric-card {
        background: linear-gradient(135deg, rgba(245, 240, 230, 0.8) 0%, rgba(250, 248, 245, 0.8) 100%);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        border: 1px solid rgba(232, 224, 213, 0.6);
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    
    .metric-card h3, .metric-card h4 {
        margin: 0 0 8px 0;
        font-family: 'Playfair Display', Georgia, serif;
        color: #1A1A1A;
    }
    
    .metric-card p {
        margin: 0;
        color: #3D3D3D;
    }
    
    /* Logo styling */
    .logo-container {
        text-align: center;
        padding: 20px;
        margin-bottom: 20px;
    }
    
    .logo-text {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.5rem;
        color: #F5F0E6;
        letter-spacing: 0.2em;
    }
    
    .logo-subtitle {
        font-size: 0.75rem;
        color: #4A7C59;
        letter-spacing: 0.3em;
        text-transform: uppercase;
        margin-top: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

load_css()

# =============================================================================
# Session State Initialization
# =============================================================================

def init_session_state():
    """Initialize all session state variables."""
    
    if "data" not in st.session_state:
        st.session_state.data = None
    
    if "params" not in st.session_state:
        st.session_state.params = GlobalParameters()
    
    if "ademe_factors" not in st.session_state:
        st.session_state.ademe_factors = copy.deepcopy(ADEME_EMISSION_FACTORS)
    
    if "scenarios" not in st.session_state:
        st.session_state.scenarios = []
    
    if "baseline" not in st.session_state:
        st.session_state.baseline = None
    
    if "optimization_result" not in st.session_state:
        st.session_state.optimization_result = None
    
    if "business_cases" not in st.session_state:
        st.session_state.business_cases = None
    
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Overview"

init_session_state()

# =============================================================================
# Data Loading
# =============================================================================

def ensure_data_loaded():
    """Ensure data is loaded, using default if necessary."""
    
    if st.session_state.data is None:
        default_path = Path(__file__).parent / "data" / "UC1_Inputs.xlsx"
        
        if not default_path.exists():
            default_path.parent.mkdir(parents=True, exist_ok=True)
            save_default_excel(default_path)
        
        try:
            st.session_state.data = load_excel_data(default_path)
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            return False
    
    return True

def recompute_baseline():
    """Recompute baseline metrics with current data and parameters."""
    if st.session_state.data is not None:
        st.session_state.baseline = compute_baseline(
            st.session_state.data,
            st.session_state.params,
            st.session_state.ademe_factors
        )

# =============================================================================
# Sidebar
# =============================================================================

def render_sidebar():
    """Render the sidebar with navigation and controls."""
    
    with st.sidebar:
        # LVMH Logo/Branding
        st.markdown("""
        <div class="logo-container">
            <div class="logo-text">LVMH</div>
            <div class="logo-subtitle">Green in Tech</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Navigation
        st.markdown("### Navigation")
        
        pages = [
            "Overview",
            "Baseline Analysis",
            "Scenario Builder",
            "Scenario Comparison",
            "Business Cases",
            "Optimization",
            "Settings",
        ]
        
        current_index = pages.index(st.session_state.current_page) if st.session_state.current_page in pages else 0
        st.session_state.current_page = st.radio(
            "Go to",
            pages,
            index=current_index,
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Data Source
        st.markdown("### Data Source")
        
        uploaded_file = st.file_uploader(
            "Upload Excel file",
            type=["xlsx", "xls"],
            help="Upload your equipment data Excel file"
        )
        
        if uploaded_file is not None:
            try:
                st.session_state.data = load_excel_data(uploaded_file)
                recompute_baseline()
                st.success("Data loaded successfully")
            except Exception as e:
                st.error(f"Error loading file: {e}")
        
        if st.button("Reset to Default Data"):
            default_path = Path(__file__).parent / "data" / "UC1_Inputs.xlsx"
            if default_path.exists():
                st.session_state.data = load_excel_data(default_path)
                recompute_baseline()
                st.success("Reset to default data")
        
        st.markdown("---")
        
        # Global Parameters
        st.markdown("### Global Parameters")
        
        params = st.session_state.params
        
        params.program_budget = st.number_input(
            "Program Budget (€/year)",
            value=int(params.program_budget),
            min_value=0,
            step=50000,
            format="%d"
        )
        
        params.target_co2_reduction = st.slider(
            "Target CO₂ Reduction (%)",
            min_value=5,
            max_value=50,
            value=int(params.target_co2_reduction * 100),
            format="%d%%"
        ) / 100
        
        params.alpha = st.slider(
            "Green ROI Weight (α)",
            min_value=0.0,
            max_value=1.0,
            value=params.alpha,
            step=0.1,
            help="α=1: Pure financial, α=0: Pure environmental"
        )
        
        st.session_state.params = params

# =============================================================================
# Page: Overview
# =============================================================================

def render_overview():
    """Render the overview/welcome page."""
    
    st.title("LVMH Green in Tech ROI Calculator")
    
    st.markdown("""
    <div class="metric-card">
        <h3>Strategic ROI Framework</h3>
        <p>Evaluate Green IT initiatives by combining financial and environmental metrics into a unified <strong>Green ROI</strong> score.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Key Objectives
    st.markdown("### Key Objectives")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h4>Target</h4>
            <p class="metric-highlight">-20%</p>
            <p>CO₂ reduction by 2026</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h4>Budget</h4>
            <p class="metric-highlight">€500k</p>
            <p>Annual program investment</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h4>Coverage</h4>
            <p class="metric-highlight">95%+</p>
            <p>Maisons participating</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Quick Start
    st.markdown("### Quick Start")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("View Baseline", use_container_width=True):
            st.session_state.current_page = "Baseline Analysis"
            st.rerun()
    
    with col2:
        if st.button("Build Scenarios", use_container_width=True):
            st.session_state.current_page = "Scenario Builder"
            st.rerun()
    
    with col3:
        if st.button("Generate Business Cases", use_container_width=True):
            st.session_state.current_page = "Business Cases"
            st.rerun()
    
    with col4:
        if st.button("Run Optimization", use_container_width=True):
            st.session_state.current_page = "Optimization"
            st.rerun()
    
    st.markdown("---")
    
    # Model Assumptions
    with st.expander("Model Assumptions"):
        st.markdown("""
        **Data Sources:**
        - Equipment counts, prices, and lifespans from Excel input
        - ADEME emission factors (editable in Settings)
        - Dell contract pricing for laptops
        
        **Calculations:**
        - Annualized Capex = (Count × Price) / (Lifespan / 12)
        - Embodied CO₂ = (Count × Emission Factor) / (Lifespan / 12)
        - Green ROI = α × Normalized Financial ROI + (1-α) × Normalized Environmental ROI
        
        **Optimization:**
        - Grid search across initiative combinations
        - Filtered by budget and CO₂ target constraints
        - Ranked by composite Green ROI score
        """)

# =============================================================================
# Page: Baseline Analysis
# =============================================================================

def render_baseline():
    """Render the baseline analysis page."""
    
    st.title("Baseline Analysis")
    st.markdown("*Current IT infrastructure footprint and emissions*")
    
    if not ensure_data_loaded():
        return
    
    recompute_baseline()
    
    baseline = st.session_state.baseline
    data = st.session_state.data
    
    if baseline is None:
        st.error("Could not compute baseline")
        return
    
    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Cost of Ownership",
            f"€{baseline.total_tco:,.0f}",
            help="Annual TCO including equipment, energy, cloud, and program costs"
        )
    
    with col2:
        st.metric(
            "Carbon Footprint",
            f"{baseline.total_co2:,.0f} kg",
            help="Annual CO₂ emissions (embodied + use phase + cloud)"
        )
    
    with col3:
        st.metric(
            "Equipment Count",
            f"{sum(data.equipment_counts.values()):,}",
            help="Total devices in inventory"
        )
    
    with col4:
        st.metric(
            "Energy Cost",
            f"€{baseline.total_energy_cost_annual:,.0f}",
            help="Annual electricity cost for IT equipment"
        )
    
    st.markdown("---")
    
    # Charts
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("### Cost Structure")
        
        cost_data = pd.DataFrame({
            "Category": list(baseline.tco_breakdown.keys()),
            "Amount": list(baseline.tco_breakdown.values())
        })
        
        fig = px.pie(
            cost_data,
            values="Amount",
            names="Category",
            hole=0.4,
            color_discrete_sequence=["#1A1A1A", "#4A7C59", "#5A9969", "#C4A35A", "#E8E0D5"]
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Montserrat", size=11),
            height=420,
            margin=dict(l=20, r=20, t=30, b=100),
            legend=dict(
                orientation="h", 
                yanchor="top", 
                y=-0.15, 
                xanchor="center", 
                x=0.5,
                font=dict(size=10)
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        st.markdown("### Emissions Distribution")
        
        co2_data = pd.DataFrame({
            "Category": list(baseline.co2_breakdown.keys()),
            "Amount": list(baseline.co2_breakdown.values())
        })
        
        fig = px.pie(
            co2_data,
            values="Amount",
            names="Category",
            hole=0.4,
            color_discrete_sequence=["#4A7C59", "#5A9969", "#3A6C49", "#C4A35A"]
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Montserrat", size=11),
            height=420,
            margin=dict(l=20, r=20, t=30, b=100),
            legend=dict(
                orientation="h", 
                yanchor="top", 
                y=-0.15, 
                xanchor="center", 
                x=0.5,
                font=dict(size=10)
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Equipment Inventory Table
    st.markdown("### Equipment Inventory")
    
    equipment_rows = []
    for equipment, count in data.equipment_counts.items():
        if count > 0:
            price = data.equipment_prices.get(equipment, 0)
            lifespan = data.equipment_lifespan.get(equipment, 48)
            capex = baseline.capex_annual.get(equipment, 0)
            co2 = baseline.co2_embodied_annual.get(equipment, 0) + baseline.co2_use_phase_annual.get(equipment, 0)
            
            equipment_rows.append({
                "Equipment": equipment,
                "Count": count,
                "Unit Price (€)": price,
                "Lifespan (months)": lifespan,
                "Annual Capex (€)": capex,
                "Annual CO₂ (kg)": co2
            })
    
    equipment_df = pd.DataFrame(equipment_rows)
    equipment_df = equipment_df.sort_values("Annual CO₂ (kg)", ascending=False)
    
    st.dataframe(
        equipment_df.style.format({
            "Count": "{:,}",
            "Unit Price (€)": "€{:,.0f}",
            "Lifespan (months)": "{:.0f}",
            "Annual Capex (€)": "€{:,.0f}",
            "Annual CO₂ (kg)": "{:,.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )

# =============================================================================
# Page: Scenario Builder
# =============================================================================

def render_scenario_builder():
    """Render the scenario builder page."""
    
    st.title("Scenario Builder")
    st.markdown("*Configure 2026 target scenarios*")
    
    if not ensure_data_loaded():
        return
    
    recompute_baseline()
    
    data = st.session_state.data
    params = st.session_state.params
    baseline = st.session_state.baseline
    
    # Quick Add Templates
    st.markdown("### Quick Add Templates")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Add Moderate Scenario", use_container_width=True):
            scenario = create_moderate_scenario()
            scenario.name = f"Moderate {len(st.session_state.scenarios) + 1}"
            st.session_state.scenarios.append(scenario)
            st.success(f"Added: {scenario.name}")
    
    with col2:
        if st.button("Add Aggressive Scenario", use_container_width=True):
            scenario = create_aggressive_scenario()
            scenario.name = f"Aggressive {len(st.session_state.scenarios) + 1}"
            st.session_state.scenarios.append(scenario)
            st.success(f"Added: {scenario.name}")
    
    with col3:
        if st.button("Clear All Scenarios", use_container_width=True):
            st.session_state.scenarios = []
            st.info("All scenarios cleared")
    
    st.markdown("---")
    
    # Custom Scenario Builder
    st.markdown("### Create Custom Scenario")
    
    with st.form("custom_scenario_form"):
        scenario_name = st.text_input("Scenario Name", value="Custom Scenario")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Device Reductions**")
            screen_reduction = st.slider("Screen Reduction (%)", 0, 50, 20) / 100
            landline_reduction = st.slider("Landline Reduction (%)", 0, 100, 100) / 100
            tablet_reduction = st.slider("Tablet Reduction (%)", 0, 50, 0) / 100
        
        with col2:
            st.markdown("**Sourcing & Lifecycle**")
            laptop_refurb_share = st.slider("Laptop Refurbished Share (%)", 0, 80, 30) / 100
            laptop_lifespan_ext = st.slider("Laptop Lifespan Extension (%)", 0, 50, 20) / 100
            screen_lifespan_ext = st.slider("Screen Lifespan Extension (%)", 0, 50, 10) / 100
        
        st.markdown("**Infrastructure**")
        col1, col2 = st.columns(2)
        with col1:
            cloud_reduction = st.slider("Cloud Cost Reduction (%)", 0, 30, 15) / 100
        with col2:
            onprem_reduction = st.slider("On-Prem Reduction (%)", 0, 20, 10) / 100
        
        if st.form_submit_button("Add Custom Scenario", type="primary"):
            new_scenario = ScenarioParams(
                name=scenario_name,
                device_reductions={
                    "Screen": screen_reduction,
                    "Landline phone": landline_reduction,
                    "Tablet": tablet_reduction,
                },
                sourcing_mix={
                    "Laptop": {"new": 1 - laptop_refurb_share, "refurb": laptop_refurb_share, "lease": 0}
                },
                lifespan_extensions={
                    "Laptop": laptop_lifespan_ext,
                    "Screen": screen_lifespan_ext,
                },
                cloud_cost_reduction=cloud_reduction,
                onprem_reduction=onprem_reduction,
                program_cost=params.program_budget
            )
            st.session_state.scenarios.append(new_scenario)
            st.success(f"Added: {scenario_name}")
    
    st.markdown("---")
    
    # Existing Scenarios
    st.markdown("### Current Scenarios")
    
    if not st.session_state.scenarios:
        st.info("No scenarios created yet. Use the templates or custom builder above.")
    else:
        for i, scenario in enumerate(st.session_state.scenarios):
            with st.expander(f"{scenario.name}"):
                # Compute metrics for this scenario
                metrics = compute_scenario(data, baseline, scenario, params, st.session_state.ademe_factors)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    # Use operational_tco (excludes program cost) for comparison with baseline
                    savings = baseline.total_tco - metrics.operational_tco
                    
                    # Streamlit delta_color:
                    # - "normal": positive = green, negative = red
                    # - "inverse": positive = red, negative = green
                    # 
                    # We show "-€X" when savings > 0 (costs went down = good)
                    # Since "-€X" is negative, we need "inverse" to make it GREEN
                    if savings > 0:
                        delta_display = f"-€{savings:,.0f}"
                        delta_color = "inverse"  # Green for negative (down arrow)
                    else:
                        delta_display = f"+€{abs(savings):,.0f}"
                        delta_color = "inverse"  # Red for positive (up arrow)
                    st.metric("TCO", f"€{metrics.operational_tco:,.0f}", delta_display, delta_color=delta_color)
                
                with col2:
                    # CO2 reduction (positive diff = good, we reduced emissions)
                    co2_diff = baseline.total_co2 - metrics.total_co2
                    co2_reduction_pct = (co2_diff / baseline.total_co2 * 100) if baseline.total_co2 > 0 else 0
                    
                    # Same logic: negative delta = improvement = should be GREEN
                    if co2_diff > 0:
                        delta_display = f"-{co2_reduction_pct:.1f}%"
                        delta_color = "inverse"  # Green for negative (down arrow)
                    else:
                        delta_display = f"+{abs(co2_reduction_pct):.1f}%"
                        delta_color = "inverse"  # Red for positive (up arrow)
                    st.metric("CO₂", f"{metrics.total_co2:,.0f} kg", delta_display, delta_color=delta_color)
                
                with col3:
                    meets_target = co2_reduction_pct >= params.target_co2_reduction * 100
                    st.metric("Meets Target", "Yes" if meets_target else "No")
                
                with col4:
                    if st.button("Remove", key=f"remove_{i}"):
                        st.session_state.scenarios.pop(i)
                        st.rerun()

# =============================================================================
# Page: Scenario Comparison
# =============================================================================

def render_comparison():
    """Render the scenario comparison page."""
    
    st.title("Scenario Comparison")
    st.markdown("*Compare scenarios side-by-side*")
    
    if not ensure_data_loaded():
        return
    
    if not st.session_state.scenarios:
        st.warning("No scenarios to compare. Create scenarios in the Scenario Builder first.")
        if st.button("Go to Scenario Builder"):
            st.session_state.current_page = "Scenario Builder"
            st.rerun()
        return
    
    recompute_baseline()
    
    baseline = st.session_state.baseline
    data = st.session_state.data
    params = st.session_state.params
    
    # Compute all scenario metrics
    all_metrics = []
    for scenario in st.session_state.scenarios:
        metrics = compute_scenario(data, baseline, scenario, params, st.session_state.ademe_factors)
        all_metrics.append(metrics)
    
    # Compute ROI metrics
    roi_metrics = compute_all_roi_metrics(
        baseline, all_metrics, 
        params.target_co2_reduction, 
        params.program_budget,
        params.alpha
    )
    
    # Build comparison table
    comparison_data = [{
        "Scenario": "Baseline",
        "TCO (€)": baseline.total_tco,
        "Savings (€)": 0,
        "CO₂ (kg)": baseline.total_co2,
        "CO₂ Reduction": "0%",
        "Meets Target": "-",
        "Green ROI": "-"
    }]
    
    for scenario, metrics, roi in zip(st.session_state.scenarios, all_metrics, roi_metrics):
        savings = baseline.total_tco - metrics.total_tco
        co2_reduction = (baseline.total_co2 - metrics.total_co2) / baseline.total_co2
        meets_target = co2_reduction >= params.target_co2_reduction
        
        comparison_data.append({
            "Scenario": scenario.name,
            "TCO (€)": metrics.total_tco,
            "Savings (€)": savings,
            "CO₂ (kg)": metrics.total_co2,
            "CO₂ Reduction": f"{co2_reduction*100:.1f}%",
            "Meets Target": "Yes" if meets_target else "No",
            "Green ROI": f"{roi.green_roi:.3f}"
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    st.dataframe(
        comparison_df.style.format({
            "TCO (€)": "€{:,.0f}",
            "Savings (€)": "€{:,.0f}",
            "CO₂ (kg)": "{:,.0f}"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Cost Comparison")
        
        tco_data = pd.DataFrame({
            "Scenario": ["Baseline"] + [s.name for s in st.session_state.scenarios],
            "TCO": [baseline.total_tco] + [m.total_tco for m in all_metrics]
        })
        
        fig = px.bar(
            tco_data,
            x="Scenario",
            y="TCO",
            color_discrete_sequence=["#4A7C59"]
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Montserrat"),
            yaxis_title="TCO (€)"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Emissions Comparison")
        
        co2_data = pd.DataFrame({
            "Scenario": ["Baseline"] + [s.name for s in st.session_state.scenarios],
            "CO₂": [baseline.total_co2] + [m.total_co2 for m in all_metrics]
        })
        
        target_co2 = baseline.total_co2 * (1 - params.target_co2_reduction)
        
        fig = px.bar(
            co2_data,
            x="Scenario",
            y="CO₂",
            color_discrete_sequence=["#1A1A1A"]
        )
        fig.add_hline(
            y=target_co2,
            line_dash="dash",
            line_color="#C44536",
            annotation_text=f"Target: {target_co2:,.0f} kg"
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Montserrat"),
            yaxis_title="CO₂ (kg)"
        )
        st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# Page: Business Cases
# =============================================================================

def render_business_cases():
    """Render the business cases page."""
    
    st.title("Business Cases")
    st.markdown("*Actionable implementation plans for each initiative*")
    
    if not ensure_data_loaded():
        return
    
    recompute_baseline()
    
    # Generate button
    if st.button("Generate Business Cases", type="primary"):
        with st.spinner("Analyzing initiatives..."):
            st.session_state.business_cases = generate_all_business_cases(
                st.session_state.data,
                st.session_state.params,
                st.session_state.ademe_factors
            )
        st.success("Business cases generated successfully!")
    
    if st.session_state.business_cases is None:
        st.info("Click the button above to generate detailed business cases for all initiatives.")
        return
    
    cases = st.session_state.business_cases
    
    # Executive Summary
    st.markdown("### Executive Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_investment = sum(c.total_investment for c in cases)
        st.metric("Total Investment", f"€{total_investment:,.0f}")
    
    with col2:
        total_savings = sum(c.annual_cost_savings for c in cases)
        st.metric("Annual Savings", f"€{total_savings:,.0f}")
    
    with col3:
        total_co2 = sum(c.annual_co2_reduction_kg for c in cases)
        st.metric("CO₂ Reduction", f"{total_co2:,.0f} kg/yr")
    
    with col4:
        must_do_count = sum(1 for c in cases if c.recommendation == "Must Do")
        st.metric("Must Do", f"{must_do_count} initiatives")
    
    st.markdown("---")
    
    # Initiative Ranking Table
    st.markdown("### Initiative Priority Ranking")
    
    ranking_data = []
    for i, case in enumerate(cases, 1):
        ranking_data.append({
            "Rank": i,
            "Initiative": case.title,
            "Category": case.category.value,
            "Investment": f"€{case.total_investment:,.0f}",
            "Annual Savings": f"€{case.annual_cost_savings:,.0f}",
            "CO₂ Reduction": f"{case.annual_co2_reduction_kg:,.0f} kg",
            "Payback": f"{case.payback_months:.0f} mo" if case.payback_months < 999 else "N/A",
            "Risk": case.overall_risk.value if hasattr(case, 'overall_risk') else "Medium",
            "Recommendation": case.recommendation
        })
    
    st.dataframe(pd.DataFrame(ranking_data), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Detailed Business Cases
    st.markdown("### Detailed Business Cases")
    
    for case in cases:
        with st.expander(f"**{case.title}** — {case.recommendation}"):
            st.markdown(f"**Category:** {case.category.value}")
            st.markdown(f"**Scope:** {case.scope_summary}")
            
            # Key Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Investment", f"€{case.total_investment:,.0f}")
            with col2:
                st.metric("Annual Savings", f"€{case.annual_cost_savings:,.0f}")
            with col3:
                if case.payback_months < 999:
                    st.metric("Payback", f"{case.payback_months:.1f} months")
                else:
                    st.metric("Payback", "N/A")
            with col4:
                st.metric("5-Year NPV", f"€{case.five_year_npv:,.0f}")
            
            st.markdown("---")
            
            # Actions
            st.markdown("**Actions Required:**")
            for i, action in enumerate(case.actions, 1):
                prereq = " [PREREQUISITE]" if action.is_prerequisite else ""
                cost = f" (€{action.cost_euros:,.0f})" if action.cost_euros > 0 else ""
                st.markdown(f"{i}. {action.description}{prereq}{cost}")
                st.markdown(f"   *Owner: {action.owner} | Duration: {action.duration_weeks} weeks*")
            
            st.markdown("---")
            
            # Investment Breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Investment Breakdown:**")
                for item, cost in case.investment_breakdown.items():
                    st.write(f"- {item}: €{cost:,.0f}")
            
            with col2:
                st.markdown("**Returns:**")
                st.write(f"- Annual cost savings: €{case.annual_cost_savings:,.0f}")
                st.write(f"- CO₂ reduction: {case.annual_co2_reduction_kg:,.0f} kg/year ({case.co2_reduction_percent*100:.2f}%)")
                st.write(f"- 5-year savings: €{case.annual_cost_savings * 5:,.0f}")
            
            st.markdown("---")
            
            # Risks
            st.markdown("**Risk Assessment:**")
            for risk in case.risks:
                level_class = f"risk-{risk.level.value.lower()}"
                st.markdown(f"- **{risk.level.value}**: {risk.description}")
                st.markdown(f"  *Mitigation: {risk.mitigation}*")

# =============================================================================
# Page: Optimization
# =============================================================================

def render_optimization():
    """Render the optimization page."""
    
    st.title("Optimization")
    st.markdown("*Find optimal initiative combinations*")
    
    if not ensure_data_loaded():
        return
    
    recompute_baseline()
    
    data = st.session_state.data
    params = st.session_state.params
    baseline = st.session_state.baseline
    
    # Configuration
    st.markdown("### Optimization Configuration")
    st.caption("*Scenarios = combinations of all parameter values. Adjust granularity to change scenario count.*")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        max_screen_reduction = st.slider("Max Screen Reduction", 0, 50, 40) / 100
    with col2:
        max_laptop_refurb = st.slider("Max Laptop Refurb Share", 0, 80, 60) / 100
    with col3:
        max_cloud_reduction = st.slider("Max Cloud Reduction", 0, 30, 25) / 100
    with col4:
        top_n = st.number_input("Number of Results", 1, 20, 5)
    
    # Calculate dynamic ranges based on slider values
    screen_steps = [0, max_screen_reduction/2, max_screen_reduction] if max_screen_reduction > 0 else [0]
    refurb_steps = [0, max_laptop_refurb/2, max_laptop_refurb] if max_laptop_refurb > 0 else [0]
    cloud_steps = [0, max_cloud_reduction/2, max_cloud_reduction] if max_cloud_reduction > 0 else [0]
    
    # Run Optimization
    if st.button("Run Optimization", type="primary", use_container_width=False):
        with st.spinner("Evaluating scenarios..."):
            config = OptimizationConfig(
                budget=params.program_budget,
                target_reduction=params.target_co2_reduction,
                alpha=params.alpha,
                screen_reduction_range=screen_steps,
                landline_reduction_range=[0.5, 1.0],
                laptop_refurb_share_range=refurb_steps,
                cloud_reduction_range=cloud_steps,
                top_n=top_n
            )
            
            st.session_state.optimization_result = run_optimization(
                data, params, config, st.session_state.ademe_factors
            )
        
        st.success("Optimization complete!")
    
    result = st.session_state.optimization_result
    
    if result is None:
        st.info("Click 'Run Optimization' to find the best initiative combinations.")
        return
    
    # Results Summary
    st.markdown("---")
    st.markdown("### Results Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Scenarios Evaluated", f"{result.total_scenarios_evaluated:,}")
    with col2:
        st.metric("Valid Scenarios", f"{result.valid_scenarios:,}")
    with col3:
        if result.top_scenarios:
            best_roi = max(r.green_roi for _, _, r in result.top_scenarios)
            st.metric("Best Green ROI", f"{best_roi:.3f}")
    
    st.markdown("---")
    
    # Top Scenarios
    st.markdown("### Top Scenarios")
    
    if not result.top_scenarios:
        st.warning("No valid scenarios found. Try adjusting constraints or increasing budgets.")
        return
    
    for i, (scenario, metrics, roi) in enumerate(result.top_scenarios, 1):
        with st.expander(f"#{i} — Green ROI: {roi.green_roi:.3f}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Financial Performance:**")
                st.write(f"- TCO: €{metrics.total_tco:,.0f}")
                st.write(f"- Savings: €{roi.cost_savings:,.0f}")
                if roi.roi_financial and roi.roi_financial != float('inf'):
                    st.write(f"- Financial ROI: {roi.roi_financial:.1%}")
                if roi.payback_years and roi.payback_years != float('inf'):
                    st.write(f"- Payback: {roi.payback_years:.1f} years")
            
            with col2:
                st.markdown("**Environmental Performance:**")
                st.write(f"- CO₂: {metrics.total_co2:,.0f} kg")
                st.write(f"- Reduction: {roi.co2_reduction_percent*100:.1f}%")
                st.write(f"- Meets Target: {'Yes' if roi.meets_target else 'No'}")
            
            st.markdown("---")
            
            st.markdown("**Key Configuration:**")
            for device, reduction in scenario.device_reductions.items():
                if reduction > 0:
                    st.write(f"- {device} reduction: {reduction*100:.0f}%")
            
            if scenario.cloud_cost_reduction > 0:
                st.write(f"- Cloud reduction: {scenario.cloud_cost_reduction*100:.0f}%")
            
            if st.button(f"Add to Scenarios", key=f"add_scenario_{i}"):
                scenario.name = f"Optimized {i}"
                st.session_state.scenarios.append(scenario)
                st.success(f"Added: {scenario.name}")

# =============================================================================
# Page: Settings
# =============================================================================

def render_settings():
    """Render the settings page."""
    
    st.title("Configuration")
    st.markdown("*Adjust emission factors, pricing, and model parameters*")
    
    tabs = st.tabs(["Emission Factors", "Dell Contract", "Cloud Providers"])
    
    # Tab 1: Emission Factors
    with tabs[0]:
        st.markdown("### ADEME Emission Factors")
        st.info("Emission factors in kg CO₂e per device. Changes apply to all calculations.")
        
        ademe = st.session_state.ademe_factors
        
        for equipment in ["Laptop", "Smartphone", "Screen", "Tablet", "Switch/Router"]:
            if equipment in ademe:
                with st.expander(f"{equipment}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        ademe[equipment]["embodied_new"] = st.number_input(
                            f"Embodied (New) — kg CO₂e",
                            value=float(ademe[equipment].get("embodied_new", 100)),
                            min_value=0.0,
                            step=10.0,
                            key=f"{equipment}_new"
                        )
                    
                    with col2:
                        ademe[equipment]["embodied_refurb"] = st.number_input(
                            f"Embodied (Refurbished) — kg CO₂e",
                            value=float(ademe[equipment].get("embodied_refurb", 20)),
                            min_value=0.0,
                            step=5.0,
                            key=f"{equipment}_refurb"
                        )
                    
                    with col3:
                        use_phase = ademe[equipment].get("use_phase_kwh_year")
                        if use_phase is not None:
                            ademe[equipment]["use_phase_kwh_year"] = st.number_input(
                                f"Use Phase — kWh/year",
                                value=float(use_phase),
                                min_value=0.0,
                                step=5.0,
                                key=f"{equipment}_use"
                            )
        
        st.markdown("### Grid Electricity Factor")
        st.session_state.params.co2_per_kwh = st.number_input(
            "CO₂ per kWh (kg)",
            value=float(st.session_state.params.co2_per_kwh),
            min_value=0.0,
            step=0.01,
            format="%.3f",
        )
    
    # Tab 2: Dell Contract
    with tabs[1]:
        st.markdown("### Dell Contract Pricing")
        st.info("Special pricing under Dell enterprise agreement. Note: Due to volume discounts, new laptops may be cheaper than refurbished.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.session_state.params.dell_laptop_new_price = st.number_input(
                "New Laptop Price (€)",
                value=float(st.session_state.params.dell_laptop_new_price),
                min_value=0.0,
                step=50.0,
            )
        
        with col2:
            st.session_state.params.dell_laptop_refurb_price = st.number_input(
                "Refurbished Laptop Price (€)",
                value=float(st.session_state.params.dell_laptop_refurb_price),
                min_value=0.0,
                step=50.0,
            )
    
    # Tab 3: Cloud Providers
    with tabs[2]:
        st.markdown("### Cloud Provider Emission Factors")
        st.info("CO₂ emissions per euro spent on cloud services (kg CO₂e/€)")
        
        cloud_provider = st.selectbox(
            "Default Cloud Provider",
            options=list(CLOUD_CO2_FACTORS.keys()),
            index=list(CLOUD_CO2_FACTORS.keys()).index(st.session_state.params.cloud_provider)
        )
        st.session_state.params.cloud_provider = cloud_provider
        
        st.markdown("**Provider Emission Factors:**")
        for provider, factor in CLOUD_CO2_FACTORS.items():
            st.write(f"- {provider}: {factor} kg CO₂e/€")

# =============================================================================
# Main Application
# =============================================================================

def main():
    """Main application entry point."""
    
    # Render sidebar
    render_sidebar()
    
    # Render current page
    page = st.session_state.current_page
    
    if page == "Overview":
        render_overview()
    elif page == "Baseline Analysis":
        render_baseline()
    elif page == "Scenario Builder":
        render_scenario_builder()
    elif page == "Scenario Comparison":
        render_comparison()
    elif page == "Business Cases":
        render_business_cases()
    elif page == "Optimization":
        render_optimization()
    elif page == "Settings":
        render_settings()

if __name__ == "__main__":
    main()