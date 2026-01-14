"""
LVMH Green in Tech ROI Calculator - Scenario Modeling

This module handles scenario calculations for 2026 projections:
- Device stock reduction per type
- Sourcing mix (new/refurb/lease)
- Lifespan extensions
- Cloud and on-prem optimization
- Power management improvements
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from .data_loader import EquipmentData, get_equipment_lifespan, get_equipment_price
from .baseline import (
    BaselineMetrics,
    compute_annualized_capex,
    compute_embodied_co2_annual,
    get_emission_factor,
    get_use_phase_kwh,
    compute_screen_annual_kwh,
)
from .config import (
    ADEME_EMISSION_FACTORS,
    CLOUD_CO2_FACTORS,
    GlobalParameters,
    SCREEN_TYPES,
    DELL_EQUIPMENT,
)


@dataclass
class ScenarioParams:
    """
    Parameters defining a scenario for 2026 projections.
    All reduction/extension values are fractions (0.0 to 1.0).
    """
    
    name: str = "Scenario 1"
    
    # Device stock reduction per type (fraction to reduce, e.g., 0.2 = 20% fewer)
    device_reductions: Dict[str, float] = field(default_factory=dict)
    
    # Sourcing mix per device type (fractions summing to 1)
    # Format: {equipment: {"new": 0.7, "refurb": 0.2, "lease": 0.1}}
    sourcing_mix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Lifespan extension per device type (fraction, e.g., 0.2 = +20% lifespan)
    lifespan_extensions: Dict[str, float] = field(default_factory=dict)
    
    # Cloud optimization
    cloud_cost_reduction: float = 0.0  # Fraction to reduce cloud costs
    cloud_provider: str = "Azure"       # Cloud provider selection
    
    # On-prem optimization
    onprem_reduction: float = 0.0  # Fraction to reduce on-prem CO₂
    
    # Power management
    screen_hours_on: Optional[float] = None   # Override screen hours on
    screen_hours_sleep: Optional[float] = None  # Override screen hours sleep
    
    # Program cost for this scenario
    program_cost: float = 500_000.0


@dataclass
class ScenarioMetrics:
    """Container for scenario calculation results."""
    
    scenario_name: str = ""
    
    # Per-equipment metrics
    device_counts: Dict[str, int] = field(default_factory=dict)
    capex_annual: Dict[str, float] = field(default_factory=dict)
    co2_embodied_annual: Dict[str, float] = field(default_factory=dict)
    co2_use_phase_annual: Dict[str, float] = field(default_factory=dict)
    energy_kwh_annual: Dict[str, float] = field(default_factory=dict)
    energy_cost_annual: Dict[str, float] = field(default_factory=dict)
    
    # Totals
    total_capex_annual: float = 0.0
    total_co2_embodied_annual: float = 0.0
    total_co2_use_phase_annual: float = 0.0
    total_energy_kwh_annual: float = 0.0
    total_energy_cost_annual: float = 0.0
    
    # Cloud and on-prem
    cloud_cost_annual: float = 0.0
    cloud_co2_annual: float = 0.0
    onprem_co2_annual: float = 0.0
    
    # Program costs (investment, not operational)
    program_cost_annual: float = 0.0
    end_of_life_cost_annual: float = 0.0
    
    # Aggregates - IMPORTANT DISTINCTION:
    # - operational_tco: Running costs WITHOUT program investment (for comparing with baseline)
    # - total_tco: Full TCO INCLUDING program investment (for budgeting)
    operational_tco: float = 0.0  # Capex + Energy + Cloud + EOL (no program cost)
    total_tco: float = 0.0       # Operational + Program cost
    total_co2: float = 0.0


def get_default_sourcing_mix() -> Dict[str, float]:
    """Get default sourcing mix (100% new)."""
    return {"new": 1.0, "refurb": 0.0, "lease": 0.0}


def compute_scenario_device_count(
    baseline_count: int,
    reduction_fraction: float
) -> int:
    """
    Compute device count after reduction.
    
    Formula: N_d^s = N_d^base × (1 - r_d^reduced)
    """
    return int(baseline_count * (1.0 - reduction_fraction))


def compute_weighted_price(
    data: EquipmentData,
    equipment: str,
    sourcing_mix: Dict[str, float],
    params: GlobalParameters
) -> float:
    """
    Compute weighted average price based on sourcing mix.
    
    Formula: P_avg = r_new × P_new + r_refurb × P_refurb + r_lease × P_lease_equiv
    """
    mix = sourcing_mix or get_default_sourcing_mix()
    
    price_new = get_equipment_price(
        data, equipment, "new",
        params.dell_laptop_new_price,
        params.dell_laptop_refurb_price
    )
    price_refurb = get_equipment_price(
        data, equipment, "refurb",
        params.dell_laptop_new_price,
        params.dell_laptop_refurb_price
    )
    price_lease = get_equipment_price(
        data, equipment, "lease",
        params.dell_laptop_new_price,
        params.dell_laptop_refurb_price
    )
    
    return (
        mix.get("new", 1.0) * price_new +
        mix.get("refurb", 0.0) * price_refurb +
        mix.get("lease", 0.0) * price_lease
    )


def compute_weighted_emission_factor(
    equipment: str,
    sourcing_mix: Dict[str, float],
    ademe_factors: Optional[Dict] = None
) -> float:
    """
    Compute weighted average emission factor based on sourcing mix.
    
    Formula: EF_avg = r_new × EF_new + r_refurb × EF_refurb + r_lease × EF_lease
    """
    mix = sourcing_mix or get_default_sourcing_mix()
    factors = ademe_factors or ADEME_EMISSION_FACTORS
    
    ef_new = get_emission_factor(equipment, "new", factors)
    ef_refurb = get_emission_factor(equipment, "refurb", factors)
    ef_lease = get_emission_factor(equipment, "lease", factors)
    
    return (
        mix.get("new", 1.0) * ef_new +
        mix.get("refurb", 0.0) * ef_refurb +
        mix.get("lease", 0.0) * ef_lease
    )


def compute_scenario(
    data: EquipmentData,
    baseline: BaselineMetrics,
    scenario: ScenarioParams,
    params: GlobalParameters,
    ademe_factors: Optional[Dict] = None
) -> ScenarioMetrics:
    """
    Compute metrics for a 2026 scenario.
    
    This implements all scenario formulas from the specification:
    - Device stock with reductions
    - Weighted pricing for sourcing mix
    - Lifespan extensions
    - Cloud and on-prem optimization
    
    Args:
        data: EquipmentData loaded from Excel
        baseline: BaselineMetrics for comparison
        scenario: ScenarioParams defining the scenario
        params: GlobalParameters with editable settings
        ademe_factors: Optional custom ADEME emission factors
    
    Returns:
        ScenarioMetrics with all calculated values
    """
    metrics = ScenarioMetrics()
    metrics.scenario_name = scenario.name
    factors = ademe_factors or ADEME_EMISSION_FACTORS
    
    # Determine screen hours (scenario override or global params)
    screen_hours_on = scenario.screen_hours_on or params.screen_hours_on
    screen_hours_sleep = scenario.screen_hours_sleep or params.screen_hours_sleep
    
    # =========================================================================
    # Per-equipment calculations
    # =========================================================================
    for equipment, baseline_count in data.equipment_counts.items():
        if baseline_count <= 0:
            continue
        
        # Device count after reduction
        # Formula: N_d^s = N_d^base × (1 - r_d^reduced)
        reduction = scenario.device_reductions.get(equipment, 0.0)
        count = compute_scenario_device_count(baseline_count, reduction)
        metrics.device_counts[equipment] = count
        
        if count <= 0:
            continue
        
        # Lifespan with extension
        # Formula: L_d^s = L_d^base × (1 + r_life_d)
        baseline_lifespan = get_equipment_lifespan(data, equipment)
        extension = scenario.lifespan_extensions.get(equipment, 0.0)
        lifespan = int(baseline_lifespan * (1.0 + extension))
        
        # Get sourcing mix and weighted price
        sourcing_mix = scenario.sourcing_mix.get(equipment, get_default_sourcing_mix())
        weighted_price = compute_weighted_price(data, equipment, sourcing_mix, params)
        
        # Annualized capex
        # Formula: CapexAnn_d^s = (N_d^s × P_avg) / (L_d^s / 12)
        capex = compute_annualized_capex(count, weighted_price, lifespan)
        metrics.capex_annual[equipment] = capex
        metrics.total_capex_annual += capex
        
        # Weighted emission factor
        weighted_ef = compute_weighted_emission_factor(equipment, sourcing_mix, factors)
        
        # Annualized embodied CO₂
        # Formula: CO2EmbAnn_d^s = (N_d^s × EF_avg) / (L_d^s / 12)
        co2_emb = compute_embodied_co2_annual(count, lifespan, weighted_ef)
        metrics.co2_embodied_annual[equipment] = co2_emb
        metrics.total_co2_embodied_annual += co2_emb
        
        # Use-phase energy (with scenario screen hours)
        if equipment in SCREEN_TYPES or "screen" in equipment.lower():
            kwh_per_device = compute_screen_annual_kwh(
                data.screen_power_on_kw,
                data.screen_power_sleep_kw,
                screen_hours_on,
                screen_hours_sleep
            )
        else:
            kwh_per_device = get_use_phase_kwh(equipment, data, params, factors)
        
        total_kwh = count * kwh_per_device
        metrics.energy_kwh_annual[equipment] = total_kwh
        metrics.total_energy_kwh_annual += total_kwh
        
        # Energy cost
        energy_cost = total_kwh * data.electricity_price_kwh
        metrics.energy_cost_annual[equipment] = energy_cost
        metrics.total_energy_cost_annual += energy_cost
        
        # Use-phase CO₂
        co2_use = total_kwh * params.co2_per_kwh
        metrics.co2_use_phase_annual[equipment] = co2_use
        metrics.total_co2_use_phase_annual += co2_use
    
    # =========================================================================
    # Cloud optimization
    # =========================================================================
    # Formula: CostCloud^s = CostCloud^base × (1 - r_cloud_cost)
    metrics.cloud_cost_annual = baseline.cloud_cost_annual * (1.0 - scenario.cloud_cost_reduction)
    
    # CO₂ with potentially different provider
    # Formula: CO2Cloud^s = CostCloud^s × EF_provider
    cloud_factor = CLOUD_CO2_FACTORS.get(scenario.cloud_provider, 0.0004)
    metrics.cloud_co2_annual = metrics.cloud_cost_annual * cloud_factor
    
    # =========================================================================
    # On-prem optimization
    # =========================================================================
    # Formula: CO2OnPrem^s = CO2OnPrem^base × (1 - r_onprem)
    metrics.onprem_co2_annual = baseline.onprem_co2_annual * (1.0 - scenario.onprem_reduction)
    
    # =========================================================================
    # Program and end-of-life costs
    # =========================================================================
    metrics.program_cost_annual = scenario.program_cost
    metrics.end_of_life_cost_annual = params.end_of_life_cost
    
    # =========================================================================
    # Aggregate totals
    # =========================================================================
    
    # Operational TCO (excludes program investment - for comparing with baseline)
    # This answers: "What are the running costs after implementing the scenario?"
    metrics.operational_tco = (
        metrics.total_capex_annual +
        metrics.total_energy_cost_annual +
        metrics.cloud_cost_annual +
        metrics.end_of_life_cost_annual
    )
    
    # Full TCO (includes program investment - for budgeting purposes)
    # This answers: "What is the total cost including the investment?"
    metrics.total_tco = metrics.operational_tco + metrics.program_cost_annual
    
    metrics.total_co2 = (
        metrics.total_co2_embodied_annual +
        metrics.total_co2_use_phase_annual +
        metrics.cloud_co2_annual +
        metrics.onprem_co2_annual
    )
    
    return metrics


def create_default_scenario() -> ScenarioParams:
    """Create a default scenario with no changes (baseline replica)."""
    return ScenarioParams(
        name="Baseline (No Changes)",
        device_reductions={},
        sourcing_mix={},
        lifespan_extensions={},
        cloud_cost_reduction=0.0,
        cloud_provider="Azure",
        onprem_reduction=0.0,
        program_cost=500_000.0,
    )


def create_moderate_scenario() -> ScenarioParams:
    """Create a moderate optimization scenario."""
    return ScenarioParams(
        name="Moderate Optimization",
        device_reductions={
            "Screen": 0.15,           # 15% screen reduction
            "Landline phone": 0.50,   # 50% landline reduction
        },
        sourcing_mix={
            "Laptop": {"new": 0.7, "refurb": 0.3, "lease": 0.0},
        },
        lifespan_extensions={
            "Laptop": 0.10,           # +10% laptop lifespan
            "Screen": 0.10,           # +10% screen lifespan
        },
        cloud_cost_reduction=0.10,    # 10% cloud cost reduction
        cloud_provider="Azure",
        onprem_reduction=0.05,        # 5% on-prem reduction
        screen_hours_on=7.0,          # Reduced screen-on time
        program_cost=500_000.0,
    )


def create_aggressive_scenario() -> ScenarioParams:
    """Create an aggressive optimization scenario targeting >20% CO₂ reduction."""
    return ScenarioParams(
        name="Aggressive Optimization",
        device_reductions={
            "Screen": 0.30,           # 30% screen reduction
            "Landline phone": 1.00,   # 100% landline removal (Teams migration)
            "Tablet": 0.20,           # 20% tablet reduction
        },
        sourcing_mix={
            "Laptop": {"new": 0.5, "refurb": 0.4, "lease": 0.1},
            "Smartphone": {"new": 0.7, "refurb": 0.3, "lease": 0.0},
        },
        lifespan_extensions={
            "Laptop": 0.20,           # +20% laptop lifespan
            "Screen": 0.15,           # +15% screen lifespan
            "Smartphone": 0.20,       # +20% smartphone lifespan
        },
        cloud_cost_reduction=0.20,    # 20% cloud cost reduction
        cloud_provider="Alternative", # Switch to greener provider
        onprem_reduction=0.15,        # 15% on-prem reduction
        screen_hours_on=6.0,          # Aggressive screen-on time reduction
        program_cost=500_000.0,
    )
