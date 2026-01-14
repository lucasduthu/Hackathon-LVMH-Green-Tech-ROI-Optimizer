"""
LVMH Green in Tech ROI Calculator - Baseline Calculations

This module computes the baseline (current state) metrics:
- Annualized capex per equipment type
- Embodied CO₂ emissions
- Use-phase energy consumption and CO₂
- Cloud and on-prem CO₂ estimation
- Total TCO and carbon footprint
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from .data_loader import EquipmentData, get_equipment_lifespan
from .config import (
    ADEME_EMISSION_FACTORS, 
    ELECTRICITY_CO2_PER_KWH,
    CLOUD_CO2_FACTORS,
    GlobalParameters,
    SCREEN_TYPES,
)


@dataclass
class BaselineMetrics:
    """Container for all baseline calculation results."""
    
    # Per-equipment metrics
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
    
    # Program costs
    program_cost_annual: float = 0.0
    end_of_life_cost_annual: float = 0.0
    
    # Aggregates
    total_tco: float = 0.0
    total_co2: float = 0.0
    
    # Breakdown percentages (for dashboard)
    co2_breakdown: Dict[str, float] = field(default_factory=dict)
    tco_breakdown: Dict[str, float] = field(default_factory=dict)


def compute_annualized_capex(
    count: int, 
    price: float, 
    lifespan_months: int
) -> float:
    """
    Compute annualized capital expenditure for equipment.
    
    Formula: CapexAnn = (N × P) / (L / 12)
    
    Args:
        count: Number of devices
        price: Unit price in euros
        lifespan_months: Equipment lifespan in months
    
    Returns:
        Annualized capex in euros
    """
    if lifespan_months <= 0:
        return 0.0
    lifespan_years = lifespan_months / 12
    return (count * price) / lifespan_years


def compute_embodied_co2_annual(
    count: int,
    lifespan_months: int,
    emission_factor: float
) -> float:
    """
    Compute annualized embodied CO₂ for equipment.
    
    Formula: CO2EmbAnn = (N × EF) / (L / 12)
    
    Args:
        count: Number of devices
        lifespan_months: Equipment lifespan in months
        emission_factor: Embodied CO₂ in kg per device
    
    Returns:
        Annualized CO₂ in kg
    """
    if lifespan_months <= 0:
        return 0.0
    lifespan_years = lifespan_months / 12
    return (count * emission_factor) / lifespan_years


def compute_screen_annual_kwh(
    power_on_kw: float,
    power_sleep_kw: float,
    hours_on: float,
    hours_sleep: float
) -> float:
    """
    Compute annual energy consumption for a single screen.
    
    Formula: kWhAnn = (P_on × H_on + P_sleep × H_sleep) × 365
    
    Args:
        power_on_kw: Power consumption when on (kW)
        power_sleep_kw: Power consumption in sleep mode (kW)
        hours_on: Hours per day screen is on
        hours_sleep: Hours per day screen is in sleep mode
    
    Returns:
        Annual kWh per screen
    """
    daily_kwh = power_on_kw * hours_on + power_sleep_kw * hours_sleep
    return daily_kwh * 365


def get_emission_factor(
    equipment: str, 
    sourcing: str = "new",
    ademe_factors: Optional[Dict] = None
) -> float:
    """
    Get emission factor for equipment type and sourcing.
    
    Args:
        equipment: Equipment type name
        sourcing: "new", "refurb", or "lease"
        ademe_factors: Optional custom ADEME factors dict
    
    Returns:
        Embodied CO₂ in kg per device
    """
    factors = ademe_factors or ADEME_EMISSION_FACTORS
    
    # Try exact match first
    if equipment in factors:
        factor_key = f"embodied_{sourcing}"
        if factor_key in factors[equipment]:
            return factors[equipment][factor_key]
        return factors[equipment].get("embodied_new", 100.0)
    
    # Try partial match for refurbished items
    for key in factors:
        if equipment.lower() in key.lower() or key.lower() in equipment.lower():
            factor_key = f"embodied_{sourcing}"
            if factor_key in factors[key]:
                return factors[key][factor_key]
            return factors[key].get("embodied_new", 100.0)
    
    # Default fallback
    return 100.0


def get_use_phase_kwh(
    equipment: str,
    data: EquipmentData,
    params: GlobalParameters,
    ademe_factors: Optional[Dict] = None
) -> float:
    """
    Get annual use-phase energy consumption for equipment.
    
    Args:
        equipment: Equipment type name
        data: EquipmentData instance
        params: GlobalParameters instance
        ademe_factors: Optional custom ADEME factors
    
    Returns:
        Annual kWh per device
    """
    factors = ademe_factors or ADEME_EMISSION_FACTORS
    
    # Special handling for screens - calculate from power consumption
    if equipment in SCREEN_TYPES or "screen" in equipment.lower():
        return compute_screen_annual_kwh(
            data.screen_power_on_kw,
            data.screen_power_sleep_kw,
            params.screen_hours_on,
            params.screen_hours_sleep
        )
    
    # Look up use phase consumption from ADEME factors
    if equipment in factors:
        kwh = factors[equipment].get("use_phase_kwh_year")
        if kwh is not None:
            return kwh
    
    # Try partial match
    for key in factors:
        if equipment.lower() in key.lower():
            kwh = factors[key].get("use_phase_kwh_year")
            if kwh is not None:
                return kwh
    
    # Default: assume minimal use-phase energy
    return 10.0


def compute_baseline(
    data: EquipmentData,
    params: GlobalParameters,
    ademe_factors: Optional[Dict] = None
) -> BaselineMetrics:
    """
    Compute complete baseline metrics for current state.
    
    This implements the baseline model from the specification:
    - Annualized capex for all equipment
    - Annualized embodied CO₂ (assuming current stock is "new")
    - Use-phase energy and CO₂ for screens and other devices
    - Cloud and on-prem CO₂ estimation (60/20/30 split)
    - Total TCO and carbon footprint
    
    Args:
        data: EquipmentData loaded from Excel
        params: GlobalParameters with editable settings
        ademe_factors: Optional custom ADEME emission factors
    
    Returns:
        BaselineMetrics with all calculated values
    """
    metrics = BaselineMetrics()
    factors = ademe_factors or ADEME_EMISSION_FACTORS
    
    # =========================================================================
    # Per-equipment calculations
    # =========================================================================
    for equipment, count in data.equipment_counts.items():
        if count <= 0:
            continue
        
        # Get equipment parameters
        lifespan = get_equipment_lifespan(data, equipment)
        price = data.equipment_prices.get(equipment, 0)
        
        # Annualized capex
        # Formula: CapexAnn_d = (N_d × P_d) / (L_d / 12)
        capex = compute_annualized_capex(count, price, lifespan)
        metrics.capex_annual[equipment] = capex
        metrics.total_capex_annual += capex
        
        # Determine if this is already refurbished stock
        is_refurbished = "refurbished" in equipment.lower()
        sourcing = "refurb" if is_refurbished else "new"
        
        # Annualized embodied CO₂
        # Formula: CO2EmbAnn_d = (N_d × EF_emb_d) / (L_d / 12)
        emission_factor = get_emission_factor(equipment, sourcing, factors)
        co2_emb = compute_embodied_co2_annual(count, lifespan, emission_factor)
        metrics.co2_embodied_annual[equipment] = co2_emb
        metrics.total_co2_embodied_annual += co2_emb
        
        # Use-phase energy and CO₂
        # Formula: kWhAnn = (P_on × H_on + P_sleep × H_sleep) × 365
        kwh_per_device = get_use_phase_kwh(equipment, data, params, factors)
        total_kwh = count * kwh_per_device
        metrics.energy_kwh_annual[equipment] = total_kwh
        metrics.total_energy_kwh_annual += total_kwh
        
        # Energy cost
        # Formula: CostEnergy = N × kWhAnn × P_kWh
        energy_cost = total_kwh * data.electricity_price_kwh
        metrics.energy_cost_annual[equipment] = energy_cost
        metrics.total_energy_cost_annual += energy_cost
        
        # Use-phase CO₂
        # Formula: CO2Use = N × kWhAnn × EF_elec
        co2_use = total_kwh * params.co2_per_kwh
        metrics.co2_use_phase_annual[equipment] = co2_use
        metrics.total_co2_use_phase_annual += co2_use
    
    # =========================================================================
    # Cloud and on-prem calculations
    # =========================================================================
    
    # Cloud cost and CO₂
    # Formula: CostCloud = 200,000 € (from Excel)
    # Formula: CO2Cloud = CostCloud × EF_cloud
    metrics.cloud_cost_annual = data.annual_cloud_consumption
    cloud_factor = CLOUD_CO2_FACTORS.get(params.cloud_provider, 0.0004)
    metrics.cloud_co2_annual = metrics.cloud_cost_annual * cloud_factor
    
    # On-prem CO₂ estimation to match LVMH 60/20/30 split
    # Equipment ≈ 60%, On-prem ≈ 20%, Cloud ≈ 30%
    # We derive on-prem from the target split
    equipment_co2 = metrics.total_co2_embodied_annual + metrics.total_co2_use_phase_annual
    
    # If cloud is 30% of total, then total = cloud / 0.30
    # On-prem = total × 0.20 = (cloud / 0.30) × 0.20
    if metrics.cloud_co2_annual > 0:
        estimated_total = metrics.cloud_co2_annual / 0.30
        metrics.onprem_co2_annual = estimated_total * 0.20
    else:
        # Fallback: estimate on-prem as 1/3 of equipment CO₂
        metrics.onprem_co2_annual = equipment_co2 * 0.33
    
    # =========================================================================
    # End-of-life costs (baseline has no program costs - that's an investment)
    # =========================================================================
    metrics.program_cost_annual = 0.0  # Baseline has no program investment
    metrics.end_of_life_cost_annual = params.end_of_life_cost
    
    # =========================================================================
    # Aggregate totals
    # =========================================================================
    
    # Total TCO (baseline = operational costs only, no program investment)
    # Formula: TCO = CapexAnn + CostEnergy + CostCloud + EOLCost
    # Note: Program cost is NOT included in baseline - it's an investment for scenarios
    metrics.total_tco = (
        metrics.total_capex_annual +
        metrics.total_energy_cost_annual +
        metrics.cloud_cost_annual +
        metrics.end_of_life_cost_annual
    )
    
    # Total CO₂
    # Formula: CO2 = CO2EmbAnn + CO2Use + CO2Cloud + CO2OnPrem
    metrics.total_co2 = (
        metrics.total_co2_embodied_annual +
        metrics.total_co2_use_phase_annual +
        metrics.cloud_co2_annual +
        metrics.onprem_co2_annual
    )
    
    # =========================================================================
    # Breakdown percentages for dashboard
    # =========================================================================
    if metrics.total_co2 > 0:
        metrics.co2_breakdown = {
            "Equipment (Embodied)": metrics.total_co2_embodied_annual / metrics.total_co2 * 100,
            "Equipment (Use Phase)": metrics.total_co2_use_phase_annual / metrics.total_co2 * 100,
            "Cloud": metrics.cloud_co2_annual / metrics.total_co2 * 100,
            "On-Premises": metrics.onprem_co2_annual / metrics.total_co2 * 100,
        }
    
    if metrics.total_tco > 0:
        metrics.tco_breakdown = {
            "Equipment (Capex)": metrics.total_capex_annual / metrics.total_tco * 100,
            "Energy": metrics.total_energy_cost_annual / metrics.total_tco * 100,
            "Cloud": metrics.cloud_cost_annual / metrics.total_tco * 100,
            "Program": metrics.program_cost_annual / metrics.total_tco * 100,
            "End-of-Life": metrics.end_of_life_cost_annual / metrics.total_tco * 100,
        }
    
    return metrics
