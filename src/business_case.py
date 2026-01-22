"""
LVMH Green in Tech ROI Calculator - Business Case Generator

This module generates professional, actionable business cases for each
Green IT initiative with:
- Detailed scope and actions
- Investment requirements with breakdown
- Financial and environmental returns
- Risk assessment
- Implementation timeline
- Ownership assignment
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import math

from .data_loader import EquipmentData
from .config import GlobalParameters, ADEME_EMISSION_FACTORS
from .baseline import BaselineMetrics, compute_baseline
from .scenario import ScenarioParams, ScenarioMetrics, compute_scenario


class RiskLevel(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class InitiativeCategory(Enum):
    EQUIPMENT = "Equipment Lifecycle"
    SOURCING = "Sourcing Strategy"
    CLOUD = "Cloud Optimization"
    INFRASTRUCTURE = "Infrastructure"
    BEHAVIOR = "Behavioral Change"


@dataclass
class ActionItem:
    """A specific action required to implement an initiative."""
    description: str
    owner: str  # Department responsible
    duration_weeks: int
    cost_euros: float = 0.0
    is_prerequisite: bool = False


@dataclass
class RiskItem:
    """A risk associated with an initiative."""
    description: str
    level: RiskLevel
    mitigation: str


@dataclass
class BusinessCase:
    """Complete business case for a Green IT initiative."""
    
    # Identity
    initiative_id: str
    title: str
    category: InitiativeCategory
    
    # Scope
    scope_summary: str
    target_description: str
    affected_equipment: Dict[str, int] = field(default_factory=dict)  # Equipment -> count affected
    
    # Actions
    actions: List[ActionItem] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    
    # Investment
    total_investment: float = 0.0
    investment_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # Returns
    annual_cost_savings: float = 0.0
    five_year_savings: float = 0.0
    annual_co2_reduction_kg: float = 0.0
    co2_reduction_percent: float = 0.0
    payback_months: float = 0.0
    five_year_npv: float = 0.0
    
    # Risk
    risks: List[RiskItem] = field(default_factory=list)
    overall_risk: RiskLevel = RiskLevel.LOW
    
    # Implementation
    owner_department: str = ""
    supporting_departments: List[str] = field(default_factory=list)
    implementation_weeks: int = 0
    recommended_quarter: str = ""
    
    # Priority
    priority_score: float = 0.0
    recommendation: str = ""  # "Must Do", "Should Do", "Consider"
    
    # Formula Explanations (for tooltips)
    investment_formula: str = ""
    savings_formula: str = ""
    co2_formula: str = ""


def calculate_npv(annual_savings: float, investment: float, years: int = 5, discount_rate: float = 0.05) -> float:
    """Calculate Net Present Value of an initiative."""
    npv = -investment
    for year in range(1, years + 1):
        npv += annual_savings / ((1 + discount_rate) ** year)
    return npv


def generate_laptop_lifespan_business_case(
    data: EquipmentData,
    baseline: BaselineMetrics,
    params: GlobalParameters,
    extension_percent: float = 0.20
) -> BusinessCase:
    """
    Generate business case for laptop lifespan extension initiative.
    
    Simple Model:
    - Investment = Cost to upgrade eligible devices (one-time)
    - Return = Value of extended life (1yr of laptop value per device)
    - Savings = Return - Investment
    - CO₂ = Avoided embodied emissions from not manufacturing replacements
    """
    
    laptop_count = data.equipment_counts.get("Laptop", 0)
    current_lifespan_months = data.equipment_lifespan.get("Laptop", 60)
    current_lifespan_years = current_lifespan_months / 12
    
    # Calculate devices eligible for upgrade
    eligible_for_upgrade = int(laptop_count * params.laptop_eligible_upgrade_percent)
    
    # Extension gives us X extra years per device
    extension_years = current_lifespan_years * extension_percent  # e.g., 5yr × 20% = 1yr
    
    laptop_price = params.dell_laptop_new_price
    upgrade_cost_per_device = params.laptop_upgrade_cost_per_unit
    
    # =========================================================================
    # INVESTMENT: Total cost to upgrade all eligible devices (one-time)
    # =========================================================================
    total_investment = eligible_for_upgrade * upgrade_cost_per_device
    
    # =========================================================================
    # RETURN: Value of extended life
    # Each laptop costs €700 over 5 years = €140/year
    # Extension of 1 year = €140 value per device
    # For all eligible: €140 × 400 = €56,000
    # =========================================================================
    annual_value_per_laptop = laptop_price / current_lifespan_years if current_lifespan_years > 0 else 0
    value_of_extension = eligible_for_upgrade * annual_value_per_laptop * extension_years
    
    # =========================================================================
    # SAVINGS: Return - Investment (one-time)
    # =========================================================================
    net_savings = value_of_extension - total_investment
    
    # =========================================================================
    # CO₂: Avoided embodied emissions
    # By extending life by 1 year, we avoid manufacturing new laptops
    # CO₂ avoided = (eligible / lifespan) × extension × embodied_co2
    # =========================================================================
    ef_laptop = ADEME_EMISSION_FACTORS.get("Laptop", {}).get("embodied_new", 300)
    avoided_laptops = eligible_for_upgrade * (extension_years / current_lifespan_years) if current_lifespan_years > 0 else 0
    co2_reduction = avoided_laptops * ef_laptop
    co2_reduction_pct = co2_reduction / baseline.total_co2 if baseline.total_co2 > 0 else 0
    
    # Simple ROI and payback (one-time basis)
    roi_percent = (net_savings / total_investment * 100) if total_investment > 0 else 0
    # Payback doesn't apply for one-time savings, but we can express it
    payback_months = 0 if net_savings >= total_investment else float('inf')
    
    return BusinessCase(
        initiative_id="I1",
        title="Laptop Upgrade Program (Extend Lifespan)",
        category=InitiativeCategory.EQUIPMENT,
        
        scope_summary=f"Upgrade {eligible_for_upgrade:,} laptops to extend lifespan by {extension_years:.1f} year(s)",
        target_description=f"Invest €{total_investment:,.0f} to preserve €{value_of_extension:,.0f} of laptop value",
        affected_equipment={"Laptop": eligible_for_upgrade},
        
        actions=[
            ActionItem("Audit laptop fleet to identify upgrade candidates", "IT Asset Management", 2, 0, True),
            ActionItem(f"Procure upgrade components for {eligible_for_upgrade} devices", "Procurement", 3, total_investment * 0.1),
            ActionItem(f"Perform upgrades on {eligible_for_upgrade} laptops", "IT Support", 6, total_investment * 0.9),
            ActionItem("Update asset records with extended lifespan", "IT Asset Management", 1, 0),
        ],
        prerequisites=[
            "Laptop fleet inventory with age data",
            "Vendor contract for upgrade components (RAM, SSD, battery)",
        ],
        
        total_investment=total_investment,
        investment_breakdown={
            f"Upgrade cost ({eligible_for_upgrade} × €{upgrade_cost_per_device:.0f})": total_investment,
        },
        
        annual_cost_savings=net_savings,  # One-time savings (field name kept for compatibility)
        five_year_savings=net_savings,    # Same as above (one-time, not recurring)
        annual_co2_reduction_kg=co2_reduction,  # One-time CO₂ avoided
        co2_reduction_percent=co2_reduction_pct,
        payback_months=payback_months,
        five_year_npv=net_savings,  # Simple: NPV = net savings for one-time
        
        risks=[
            RiskItem("Upgraded devices may still fail earlier than expected", RiskLevel.LOW, "Include warranty on upgrade components"),
            RiskItem("User perception of old hardware", RiskLevel.LOW, "Communicate sustainability benefits"),
        ],
        overall_risk=RiskLevel.LOW,
        
        owner_department="IT Procurement",
        supporting_departments=["IT Support", "Finance"],
        implementation_weeks=8,
        recommended_quarter="Q1 2026",
        
        priority_score=0.0,
        recommendation="",
        
        # Formula explanations for tooltips
        investment_formula=f"{eligible_for_upgrade:,} laptops × €{upgrade_cost_per_device:.0f}/upgrade = €{total_investment:,.0f}",
        savings_formula=f"Value of extension: {eligible_for_upgrade:,} × €{annual_value_per_laptop:.0f}/yr × {extension_years:.1f}yr = €{value_of_extension:,.0f}\nMinus investment: €{value_of_extension:,.0f} - €{total_investment:,.0f} = €{net_savings:,.0f}",
        co2_formula=f"Avoided laptops: {avoided_laptops:.0f}\nEmbodied CO₂: {avoided_laptops:.0f} × {ef_laptop} kg = {co2_reduction:,.0f} kg",
    )


def generate_refurbished_sourcing_business_case(
    data: EquipmentData,
    baseline: BaselineMetrics,
    params: GlobalParameters,
) -> BusinessCase:
    """
    Generate business case for refurbished laptop sourcing initiative.
    
    Simple Model:
    - Investment = Total spend on refurbished laptops
    - Baseline = What new laptops would have cost
    - Savings = Baseline - Investment (negative if refurb costs more)
    - CO₂ = Avoided embodied emissions (refurb vs new)
    """
    
    laptop_count = data.equipment_counts.get("Laptop", 0)
    lifespan_months = data.equipment_lifespan.get("Laptop", 60)
    lifespan_years = lifespan_months / 12
    
    # Annual replacement rate (laptops that need replacing each year)
    annual_replacements = laptop_count / lifespan_years if lifespan_years > 0 else 0
    
    # Number of refurbished units to purchase
    refurb_share = params.refurb_share_percent
    refurb_quantity = int(annual_replacements * refurb_share)
    
    new_price = params.dell_laptop_new_price
    refurb_price = params.dell_laptop_refurb_price
    
    # =========================================================================
    # INVESTMENT: Total spend on refurbished laptops
    # =========================================================================
    total_investment = refurb_quantity * refurb_price
    
    # =========================================================================
    # BASELINE: What new laptops would have cost
    # =========================================================================
    baseline_cost = refurb_quantity * new_price
    
    # =========================================================================
    # SAVINGS: Baseline - Investment (negative if refurb costs more)
    # =========================================================================
    net_savings = baseline_cost - total_investment
    
    # =========================================================================
    # CO₂: Avoided embodied emissions
    # Refurbished: ~50 kg vs New: ~300 kg = 250 kg saved per device
    # =========================================================================
    ef_new = ADEME_EMISSION_FACTORS.get("Laptop", {}).get("embodied_new", 300)
    ef_refurb = ADEME_EMISSION_FACTORS.get("Laptop", {}).get("embodied_refurb", 50)
    co2_savings_per_device = ef_new - ef_refurb
    co2_reduction = refurb_quantity * co2_savings_per_device
    co2_reduction_pct = co2_reduction / baseline.total_co2 if baseline.total_co2 > 0 else 0
    
    # Cost per tonne CO₂ (useful metric for environmental initiatives)
    extra_cost = -net_savings if net_savings < 0 else 0
    cost_per_tonne = (extra_cost / (co2_reduction / 1000)) if co2_reduction > 0 and extra_cost > 0 else 0
    
    return BusinessCase(
        initiative_id="I2",
        title="Refurbished Laptop Sourcing",
        category=InitiativeCategory.SOURCING,
        
        scope_summary=f"Source {refurb_quantity} refurbished laptops ({refurb_share*100:.0f}% of annual replacements)",
        target_description=f"Investment: €{total_investment:,.0f} | Baseline (new): €{baseline_cost:,.0f} | CO₂ saved: {co2_reduction:,.0f} kg" + (f" | Cost: €{cost_per_tonne:,.0f}/tonne" if cost_per_tonne > 0 else ""),
        affected_equipment={"Laptop": refurb_quantity},
        
        actions=[
            ActionItem(f"Order {refurb_quantity} Dell Certified Refurbished laptops", "Procurement", 2, total_investment),
            ActionItem("Communicate sustainability benefits to users", "Communications", 2, 0),
        ],
        prerequisites=[
            "Dell Certified Refurbished available in contract",
        ],
        
        total_investment=total_investment,
        investment_breakdown={
            f"Refurbished laptops ({refurb_quantity} × €{refurb_price:.0f})": total_investment,
        },
        
        annual_cost_savings=net_savings,  # May be negative
        five_year_savings=net_savings,    # One-time (not multiplied)
        annual_co2_reduction_kg=co2_reduction,
        co2_reduction_percent=co2_reduction_pct,
        payback_months=0 if net_savings >= 0 else float('inf'),
        five_year_npv=net_savings,
        
        risks=[
            RiskItem("User perception of refurbished equipment", RiskLevel.LOW, "Emphasize Dell Certified quality and sustainability message"),
        ],
        overall_risk=RiskLevel.LOW,
        
        owner_department="Procurement",
        supporting_departments=["IT", "Communications"],
        implementation_weeks=4,
        recommended_quarter="Q1 2026",
        
        priority_score=0.0,
        recommendation="",
        
        investment_formula=f"{refurb_quantity} laptops × €{refurb_price:.0f} = €{total_investment:,.0f}",
        savings_formula=f"Baseline (new): {refurb_quantity} × €{new_price:.0f} = €{baseline_cost:,.0f}\nMinus investment: €{baseline_cost:,.0f} - €{total_investment:,.0f} = €{net_savings:,.0f}",
        co2_formula=f"{refurb_quantity} units × {co2_savings_per_device} kg saved = {co2_reduction:,.0f} kg",
    )


def generate_screen_reduction_business_case(
    data: EquipmentData,
    baseline: BaselineMetrics,
    params: GlobalParameters,
    reduction_percent: float = 0.30
) -> BusinessCase:
    """
    Generate business case for screen count reduction initiative.
    
    Simple Model:
    - Investment = Cost to implement (audit, hot-desking, booking system, comms)
    - Savings = Avoided screen purchases + energy savings (over lifespan)
    - CO₂ = Avoided embodied emissions + reduced energy use
    """
    
    screen_count = data.equipment_counts.get("Screen", 0)
    screens_to_remove = int(screen_count * reduction_percent)
    
    screen_price = data.equipment_prices.get("Screen", 200)
    screen_lifespan_months = data.equipment_lifespan.get("Screen", 72)
    screen_lifespan_years = screen_lifespan_months / 12
    
    # =========================================================================
    # INVESTMENT: Cost to implement the reduction
    # =========================================================================
    total_investment = (
        params.screen_audit_cost +
        params.screen_hot_desking_investment +
        params.screen_booking_system_cost +
        params.screen_communication_cost
    )
    
    # =========================================================================
    # SAVINGS: Value of screens NOT purchased + 1 year energy savings
    # =========================================================================
    # CAPEX: Value of avoided screen purchases (one-time)
    avoided_screen_value = screens_to_remove * screen_price
    
    # Energy: 1 year of energy savings (consistent with other initiatives)
    # Screen: ~0.16 kW active × 8h + ~0.005 kW sleep × 16h = 1.37 kWh/day
    annual_kwh_per_screen = (0.16 * 8 + 0.005 * 16) * 365  # ~500 kWh/year
    energy_savings_kwh = screens_to_remove * annual_kwh_per_screen
    energy_cost_savings = energy_savings_kwh * data.electricity_price_kwh  # 1 year only
    
    # Total savings (one-time: avoided screens + 1 year energy)
    total_savings = avoided_screen_value + energy_cost_savings
    net_savings = total_savings - total_investment
    
    # =========================================================================
    # CO₂: Avoided emissions (one-time embodied + 1 year use-phase)
    # =========================================================================
    ef_screen = ADEME_EMISSION_FACTORS.get("Screen", {}).get("embodied_new", 350)
    embodied_co2_avoided = screens_to_remove * ef_screen
    use_phase_co2_avoided = energy_savings_kwh * params.co2_per_kwh  # 1 year
    total_co2_reduction = embodied_co2_avoided + use_phase_co2_avoided
    co2_reduction_pct = total_co2_reduction / baseline.total_co2 if baseline.total_co2 > 0 else 0
    
    return BusinessCase(
        initiative_id="I3",
        title="Screen Count Reduction",
        category=InitiativeCategory.EQUIPMENT,
        
        scope_summary=f"Remove {screens_to_remove} screens ({reduction_percent*100:.0f}% of fleet) through workspace optimization",
        target_description=f"Investment: €{total_investment:,.0f} | Avoided value: €{avoided_screen_value:,.0f} | Net savings: €{net_savings:,.0f}",
        affected_equipment={"Screen": screens_to_remove},
        
        actions=[
            ActionItem("Conduct workspace utilization audit", "Facilities", 4, params.screen_audit_cost, True),
            ActionItem("Implement hot-desking infrastructure", "Facilities", 8, params.screen_hot_desking_investment),
            ActionItem("Deploy desk booking system", "IT", 4, params.screen_booking_system_cost),
            ActionItem(f"Decommission and recycle {screens_to_remove} screens", "IT Asset Management", 4, 0),
            ActionItem("Employee communication and change management", "HR & Comms", 4, params.screen_communication_cost),
        ],
        prerequisites=[
            "Workspace utilization data (min 4 weeks)",
            "Desk booking solution selected",
            "Change management plan approved",
        ],
        
        total_investment=total_investment,
        investment_breakdown={
            "Utilization audit": params.screen_audit_cost,
            "Hot-desking setup": params.screen_hot_desking_investment,
            "Booking system": params.screen_booking_system_cost,
            "Change management": params.screen_communication_cost,
        },
        
        annual_cost_savings=net_savings,  # One-time net savings
        five_year_savings=net_savings,
        annual_co2_reduction_kg=total_co2_reduction,  # One-time CO₂ avoided
        co2_reduction_percent=co2_reduction_pct,
        payback_months=0 if net_savings >= 0 else float('inf'),
        five_year_npv=net_savings,
        
        risks=[
            RiskItem("Employee resistance to hot-desking", RiskLevel.HIGH, "Phased rollout with pilot"),
            RiskItem("Productivity concerns", RiskLevel.MEDIUM, "Provide dual-screen zones"),
        ],
        overall_risk=RiskLevel.HIGH,
        
        owner_department="Facilities",
        supporting_departments=["IT", "HR", "Communications"],
        implementation_weeks=16,
        recommended_quarter="Q1-Q2 2026",
        
        priority_score=0.0,
        recommendation="",
        
        investment_formula=f"Audit: €{params.screen_audit_cost:,.0f} + Hot-desk: €{params.screen_hot_desking_investment:,.0f} + Booking: €{params.screen_booking_system_cost:,.0f} + Comms: €{params.screen_communication_cost:,.0f} = €{total_investment:,.0f}",
        savings_formula=f"Avoided screens: {screens_to_remove} × €{screen_price:,.0f} = €{avoided_screen_value:,.0f}\nEnergy (1yr): €{energy_cost_savings:,.0f}\nTotal: €{total_savings:,.0f} - €{total_investment:,.0f} = €{net_savings:,.0f}",
        co2_formula=f"Embodied: {screens_to_remove} × {ef_screen} kg = {embodied_co2_avoided:,.0f} kg\nUse-phase (1yr): {energy_savings_kwh:,.0f} kWh × {params.co2_per_kwh} = {use_phase_co2_avoided:,.0f} kg",
    )


def generate_landline_removal_business_case(
    data: EquipmentData,
    baseline: BaselineMetrics,
    params: GlobalParameters
) -> BusinessCase:
    """
    Generate business case for landline phone removal initiative.
    
    Simple Model:
    - Investment = Cost to implement (headsets + training + Teams licenses)
    - Savings = Value of landlines avoided + telecom contract savings
    - CO₂ = Avoided embodied emissions from landlines
    """
    
    landline_count = data.equipment_counts.get("Landline phone", 0)
    landline_price = data.equipment_prices.get("Landline phone", 350)
    landline_lifespan_months = data.equipment_lifespan.get("Landline phone", 72)
    landline_lifespan_years = landline_lifespan_months / 12
    
    # =========================================================================
    # INVESTMENT: Cost to migrate to Teams
    # =========================================================================
    headset_cost = landline_count * params.landline_headset_cost_per_unit
    training_cost = params.landline_training_cost
    teams_license_cost = params.landline_teams_license_cost
    total_investment = headset_cost + training_cost + teams_license_cost
    
    # =========================================================================
    # SAVINGS: Value of avoided landlines + 1 year telecom savings
    # =========================================================================
    # CAPEX: Value of landline handsets not purchased (one-time)
    avoided_landline_value = landline_count * landline_price
    
    # OPEX: 1 year of telecom savings (consistent with other initiatives)
    annual_telecom_cost = landline_count * params.landline_monthly_telecom_cost * 12
    telecom_savings = annual_telecom_cost  # 1 year only
    
    total_savings = avoided_landline_value + telecom_savings
    net_savings = total_savings - total_investment
    
    # =========================================================================
    # CO₂: Avoided embodied emissions
    # =========================================================================
    ef_landline = ADEME_EMISSION_FACTORS.get("Landline phone", {}).get("embodied_new", 25)
    co2_reduction = landline_count * ef_landline
    co2_reduction_pct = co2_reduction / baseline.total_co2 if baseline.total_co2 > 0 else 0
    
    return BusinessCase(
        initiative_id="I4",
        title="Landline to Teams Migration",
        category=InitiativeCategory.INFRASTRUCTURE,
        
        scope_summary=f"Remove {landline_count} landline phones, migrate to Microsoft Teams",
        target_description=f"Investment: €{total_investment:,.0f} | Avoided value: €{avoided_landline_value:,.0f} + telecom €{telecom_savings:,.0f} | Net: €{net_savings:,.0f}",
        affected_equipment={"Landline phone": landline_count},
        
        actions=[
            ActionItem("Audit current landline usage", "Telecom", 2, 0, True),
            ActionItem("Verify Teams Phone licensing", "IT", 2, teams_license_cost),
            ActionItem(f"Distribute {landline_count} headsets", "IT", 4, headset_cost),
            ActionItem("Conduct user training", "IT Training", 4, training_cost),
            ActionItem("Decommission landlines", "Telecom", 4, 0),
            ActionItem("Terminate telecom contracts", "Procurement", 2, 0),
        ],
        prerequisites=[
            "Microsoft Teams deployed",
            "Network bandwidth verified for VoIP",
        ],
        
        total_investment=total_investment,
        investment_breakdown={
            f"Headsets ({landline_count} × €{params.landline_headset_cost_per_unit:.0f})": headset_cost,
            "User training": training_cost,
            "Teams Phone licensing": teams_license_cost,
        },
        
        annual_cost_savings=net_savings,  # One-time net savings
        five_year_savings=net_savings,
        annual_co2_reduction_kg=co2_reduction,
        co2_reduction_percent=co2_reduction_pct,
        payback_months=0 if net_savings >= 0 else float('inf'),
        five_year_npv=net_savings,
        
        risks=[
            RiskItem("Network outages affecting voice", RiskLevel.MEDIUM, "Mobile backup for critical roles"),
            RiskItem("Reception desk adaptation", RiskLevel.MEDIUM, "Specialized Teams devices"),
        ],
        overall_risk=RiskLevel.MEDIUM,
        
        owner_department="Telecom",
        supporting_departments=["IT", "HR"],
        implementation_weeks=12,
        recommended_quarter="Q1-Q2 2026",
        
        priority_score=0.0,
        recommendation="",
        
        investment_formula=f"Headsets: {landline_count} × €{params.landline_headset_cost_per_unit:.0f} = €{headset_cost:,.0f}\nTraining: €{training_cost:,.0f}\nLicenses: €{teams_license_cost:,.0f}\nTotal: €{total_investment:,.0f}",
        savings_formula=f"Avoided landlines: {landline_count} × €{landline_price:.0f} = €{avoided_landline_value:,.0f}\nTelecom (1yr): €{telecom_savings:,.0f}\nTotal: €{total_savings:,.0f} - €{total_investment:,.0f} = €{net_savings:,.0f}",
        co2_formula=f"{landline_count} phones × {ef_landline} kg = {co2_reduction:,.0f} kg",
    )


def generate_cloud_finops_business_case(
    data: EquipmentData,
    baseline: BaselineMetrics,
    params: GlobalParameters,
) -> BusinessCase:
    """
    Generate business case for cloud FinOps initiative.
    
    Granular Model - 5 Strategies:
    1. Rightsizing: Resize over-provisioned VMs
    2. Reserved Instances: Commit to capacity for discounts
    3. Orphan Cleanup: Delete unused resources
    4. Scheduling: Turn off dev/test outside hours
    5. Storage Tiering: Archive cold data to cheaper tiers
    """
    
    cloud_spend = baseline.cloud_cost_annual
    
    # =========================================================================
    # INVESTMENT: Cost to implement FinOps program
    # =========================================================================
    total_investment = (
        params.cloud_finops_tool_cost +
        params.cloud_consultant_cost +
        params.cloud_training_cost
    )
    
    # =========================================================================
    # COST BREAKDOWN: Split cloud spend into compute/storage/other
    # =========================================================================
    compute_spend = cloud_spend * params.cloud_compute_share
    storage_spend = cloud_spend * params.cloud_storage_share
    # other_spend = cloud_spend * params.cloud_other_share  # Not directly optimizable
    
    # =========================================================================
    # SAVINGS: Calculate each strategy's contribution (applied to correct portion)
    # =========================================================================
    
    # Strategy 1: Rightsizing — applies to COMPUTE only
    # Savings = compute_spend × vm_share × rightsizing_savings%
    rightsizing_savings = (
        compute_spend * 
        params.finops_rightsizing_vm_share * 
        params.finops_rightsizing_savings
    )
    
    # Strategy 2: Reserved Instances — applies to COMPUTE only
    # Savings = compute_spend × workload_share × discount%
    reserved_savings = (
        compute_spend * 
        params.finops_reserved_workload_share * 
        params.finops_reserved_discount
    )
    
    # Strategy 3: Orphan Cleanup — applies to TOTAL (waste can be anywhere)
    # Savings = total_spend × orphan_waste%
    orphan_savings = cloud_spend * params.finops_orphan_waste_percent
    
    # Strategy 4: Scheduling — applies to COMPUTE only
    # Savings = compute_spend × dev_test_share × scheduling_savings%
    scheduling_savings = (
        compute_spend * 
        params.finops_dev_test_share * 
        params.finops_scheduling_savings
    )
    
    # Strategy 5: Storage Tiering — applies to STORAGE only
    # Savings = storage_spend × archivable% × discount%
    storage_savings = (
        storage_spend * 
        params.finops_archivable_data * 
        params.finops_archive_discount
    )
    
    # Total savings from all strategies
    total_cloud_savings = (
        rightsizing_savings +
        reserved_savings +
        orphan_savings +
        scheduling_savings +
        storage_savings
    )
    
    net_savings = total_cloud_savings - total_investment
    reduction_percent = total_cloud_savings / cloud_spend if cloud_spend > 0 else 0
    
    # =========================================================================
    # CO₂: Reduced cloud emissions (proportional to spend reduction)
    # =========================================================================
    from .config import CLOUD_CO2_FACTORS
    cloud_factor = CLOUD_CO2_FACTORS.get(params.cloud_provider, 0.0004)
    co2_reduction = total_cloud_savings * cloud_factor
    co2_reduction_pct = co2_reduction / baseline.total_co2 if baseline.total_co2 > 0 else 0
    
    # Build formula explanation for tooltip
    savings_breakdown = (
        f"Cost Breakdown: Compute €{compute_spend:,.0f} | Storage €{storage_spend:,.0f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Rightsizing: €{compute_spend:,.0f} × {params.finops_rightsizing_vm_share*100:.0f}% × {params.finops_rightsizing_savings*100:.0f}% = €{rightsizing_savings:,.0f}\n"
        f"Reserved: €{compute_spend:,.0f} × {params.finops_reserved_workload_share*100:.0f}% × {params.finops_reserved_discount*100:.0f}% = €{reserved_savings:,.0f}\n"
        f"Orphans: €{cloud_spend:,.0f} × {params.finops_orphan_waste_percent*100:.0f}% = €{orphan_savings:,.0f}\n"
        f"Scheduling: €{compute_spend:,.0f} × {params.finops_dev_test_share*100:.0f}% × {params.finops_scheduling_savings*100:.0f}% = €{scheduling_savings:,.0f}\n"
        f"Storage: €{storage_spend:,.0f} × {params.finops_archivable_data*100:.0f}% × {params.finops_archive_discount*100:.0f}% = €{storage_savings:,.0f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"TOTAL: €{total_cloud_savings:,.0f} ({reduction_percent*100:.1f}% reduction)"
    )
    
    return BusinessCase(
        initiative_id="I5",
        title="Cloud FinOps Optimization",
        category=InitiativeCategory.CLOUD,
        
        scope_summary=f"Reduce cloud spend by {reduction_percent*100:.1f}% (€{total_cloud_savings:,.0f}) using 5 FinOps strategies",
        target_description=f"Investment: €{total_investment:,.0f} | Savings: €{total_cloud_savings:,.0f} | Net: €{net_savings:,.0f}",
        affected_equipment={},
        
        actions=[
            ActionItem("Deploy FinOps tooling", "Cloud Team", 4, params.cloud_finops_tool_cost),
            ActionItem("Cloud cost audit with consultant", "Cloud Team", 6, params.cloud_consultant_cost),
            ActionItem(f"Rightsizing (€{rightsizing_savings:,.0f})", "Cloud Team", 4, 0),
            ActionItem(f"Reserved Instances (€{reserved_savings:,.0f})", "Cloud Team", 4, 0),
            ActionItem(f"Orphan cleanup (€{orphan_savings:,.0f})", "Cloud Team", 2, 0),
            ActionItem(f"Dev/test scheduling (€{scheduling_savings:,.0f})", "Cloud Team", 2, 0),
            ActionItem(f"Storage tiering (€{storage_savings:,.0f})", "Data Team", 4, 0),
            ActionItem("Team FinOps training", "Cloud Team", 4, params.cloud_training_cost),
        ],
        prerequisites=[
            "Cloud cost visibility tool deployed",
            "Resource tagging strategy implemented",
        ],
        
        total_investment=total_investment,
        investment_breakdown={
            "FinOps tooling": params.cloud_finops_tool_cost,
            "Consultant": params.cloud_consultant_cost,
            "Training": params.cloud_training_cost,
        },
        
        annual_cost_savings=net_savings,
        five_year_savings=net_savings,
        annual_co2_reduction_kg=co2_reduction,
        co2_reduction_percent=co2_reduction_pct,
        payback_months=0 if net_savings >= 0 else float('inf'),
        five_year_npv=net_savings,
        
        risks=[
            RiskItem("Rightsizing may impact performance", RiskLevel.MEDIUM, "Test in staging first"),
            RiskItem("Reserved Instance commitment risk", RiskLevel.LOW, "Start with 1-year terms"),
            RiskItem("Requires ongoing governance", RiskLevel.MEDIUM, "Establish FinOps practice"),
        ],
        overall_risk=RiskLevel.LOW,
        
        owner_department="Cloud/Infrastructure",
        supporting_departments=["Finance", "Development"],
        implementation_weeks=16,
        recommended_quarter="Q1 2026",
        
        priority_score=0.0,
        recommendation="",
        
        investment_formula=f"Tooling: €{params.cloud_finops_tool_cost:,.0f}\nConsultant: €{params.cloud_consultant_cost:,.0f}\nTraining: €{params.cloud_training_cost:,.0f}\nTotal: €{total_investment:,.0f}",
        savings_formula=savings_breakdown,
        co2_formula=f"€{total_cloud_savings:,.0f} × {cloud_factor} kg/€ = {co2_reduction:,.0f} kg",
    )


def generate_onprem_optimization_business_case(
    data: EquipmentData,
    baseline: BaselineMetrics,
    params: GlobalParameters,
) -> BusinessCase:
    """
    Generate business case for on-premises infrastructure optimization.
    
    Model:
    - Investment = Audit + migration + decommissioning
    - Savings = User-defined infra cost × reduction target (1 year)
    - CO₂ = Reduced on-prem emissions
    """
    
    # =========================================================================
    # INVESTMENT: Cost to consolidate infrastructure
    # =========================================================================
    total_investment = (
        params.onprem_audit_cost +
        params.onprem_migration_cost +
        params.onprem_decom_cost
    )
    
    # =========================================================================
    # SAVINGS: User-defined infrastructure cost reduction (1 year)
    # =========================================================================
    annual_infra_cost = params.onprem_annual_infra_cost
    reduction_percent = params.onprem_reduction_target
    annual_savings = annual_infra_cost * reduction_percent
    net_savings = annual_savings - total_investment
    
    # =========================================================================
    # CO₂: Reduced on-prem emissions (proportional to reduction)
    # =========================================================================
    current_onprem_co2 = baseline.onprem_co2_annual
    co2_reduction = current_onprem_co2 * reduction_percent
    co2_reduction_pct = co2_reduction / baseline.total_co2 if baseline.total_co2 > 0 else 0
    
    return BusinessCase(
        initiative_id="I6",
        title="On-Premises Consolidation",
        category=InitiativeCategory.INFRASTRUCTURE,
        
        scope_summary=f"Reduce on-prem footprint by {reduction_percent*100:.0f}% (€{annual_savings:,.0f} savings)",
        target_description=f"Investment: €{total_investment:,.0f} | Annual savings: €{annual_savings:,.0f} | Net: €{net_savings:,.0f}",
        affected_equipment={},
        
        actions=[
            ActionItem("Data center footprint audit", "Infrastructure", 6, params.onprem_audit_cost),
            ActionItem("Identify workloads for migration/consolidation", "Infrastructure", 4, 0),
            ActionItem("Execute migrations", "Infrastructure", 12, params.onprem_migration_cost),
            ActionItem("Decommission retired infrastructure", "Infrastructure", 4, params.onprem_decom_cost),
        ],
        prerequisites=[
            "Application portfolio analysis",
            "Cloud migration readiness assessment",
        ],
        
        total_investment=total_investment,
        investment_breakdown={
            "Audit": params.onprem_audit_cost,
            "Migration": params.onprem_migration_cost,
            "Decommissioning": params.onprem_decom_cost,
        },
        
        annual_cost_savings=net_savings,
        five_year_savings=net_savings,
        annual_co2_reduction_kg=co2_reduction,
        co2_reduction_percent=co2_reduction_pct,
        payback_months=0 if net_savings >= 0 else float('inf'),
        five_year_npv=net_savings,
        
        risks=[
            RiskItem("Application compatibility issues", RiskLevel.MEDIUM, "Thorough testing"),
            RiskItem("Business disruption during migration", RiskLevel.HIGH, "Off-hours execution"),
        ],
        overall_risk=RiskLevel.MEDIUM,
        
        owner_department="Infrastructure",
        supporting_departments=["Applications", "Security"],
        implementation_weeks=20,
        recommended_quarter="Q2-Q3 2026",
        
        priority_score=0.0,
        recommendation="",
        
        investment_formula=f"Audit: €{params.onprem_audit_cost:,.0f}\nMigration: €{params.onprem_migration_cost:,.0f}\nDecom: €{params.onprem_decom_cost:,.0f}\nTotal: €{total_investment:,.0f}",
        savings_formula=f"Infra cost: €{annual_infra_cost:,.0f}/yr\nReduction: {reduction_percent*100:.0f}%\nSavings: €{annual_savings:,.0f}\nNet: €{annual_savings:,.0f} - €{total_investment:,.0f} = €{net_savings:,.0f}",
        co2_formula=f"{reduction_percent*100:.0f}% × {current_onprem_co2:,.0f} kg = {co2_reduction:,.0f} kg",
    )


def generate_all_business_cases(
    data: EquipmentData,
    params: GlobalParameters,
    ademe_factors: Optional[Dict] = None
) -> List[BusinessCase]:
    """Generate business cases for all standard initiatives."""
    
    baseline = compute_baseline(data, params, ademe_factors)
    
    cases = [
        generate_laptop_lifespan_business_case(data, baseline, params),
        generate_refurbished_sourcing_business_case(data, baseline, params),
        generate_screen_reduction_business_case(data, baseline, params),
        generate_landline_removal_business_case(data, baseline, params),
        generate_cloud_finops_business_case(data, baseline, params),
        generate_onprem_optimization_business_case(data, baseline, params),
    ]
    
    # Calculate priority scores and set recommendations consistently
    max_savings = max(c.annual_cost_savings for c in cases) if cases else 1
    min_savings = min(c.annual_cost_savings for c in cases) if cases else 0
    max_co2 = max(c.annual_co2_reduction_kg for c in cases) if cases else 1
    
    # Handle negative savings by shifting to 0-1 range
    savings_range = max_savings - min_savings if max_savings != min_savings else 1
    
    for case in cases:
        # Normalize savings (handle negative values)
        savings_score = (case.annual_cost_savings - min_savings) / savings_range if savings_range > 0 else 0
        co2_score = case.annual_co2_reduction_kg / max_co2 if max_co2 > 0 else 0
        risk_penalty = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 0.1, RiskLevel.HIGH: 0.2}.get(case.overall_risk, 0)
        
        # Calculate priority score using Green ROI formula
        case.priority_score = (params.alpha * savings_score + (1 - params.alpha) * co2_score) * (1 - risk_penalty)
        
        # Set recommendation based on priority score (consistent across all initiatives)
        # Note: Thresholds adjusted for relative normalization where max realistic score ~0.6-0.7
        if case.priority_score >= 0.55:
            case.recommendation = "Must Do"
        elif case.priority_score >= 0.35:
            case.recommendation = "Should Do"
        else:
            case.recommendation = "Consider"
    
    # Sort by priority score (highest first)
    cases.sort(key=lambda c: c.priority_score, reverse=True)
    
    return cases


def format_business_case_text(case: BusinessCase) -> str:
    """Format a business case as readable text."""
    
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"INITIATIVE: {case.title}")
    lines.append(f"{'='*60}")
    lines.append("")
    lines.append(f"CATEGORY: {case.category.value}")
    lines.append(f"SCOPE: {case.scope_summary}")
    lines.append("")
    
    lines.append("ACTIONS REQUIRED:")
    for i, action in enumerate(case.actions, 1):
        prereq = " [PREREQUISITE]" if action.is_prerequisite else ""
        cost = f" (€{action.cost_euros:,.0f})" if action.cost_euros > 0 else ""
        lines.append(f"  {i}. {action.description}{prereq}{cost}")
        lines.append(f"     Owner: {action.owner} | Duration: {action.duration_weeks} weeks")
    lines.append("")
    
    lines.append(f"INVESTMENT: €{case.total_investment:,.0f}")
    for item, cost in case.investment_breakdown.items():
        lines.append(f"  - {item}: €{cost:,.0f}")
    lines.append("")
    
    lines.append("RETURNS:")
    lines.append(f"  - Annual cost savings: €{case.annual_cost_savings:,.0f}")
    lines.append(f"  - CO₂ reduction: {case.annual_co2_reduction_kg:,.0f} kg/year ({case.co2_reduction_percent*100:.2f}%)")
    if case.payback_months < float('inf'):
        lines.append(f"  - Payback period: {case.payback_months:.1f} months")
    lines.append(f"  - 5-year NPV: €{case.five_year_npv:,.0f}")
    lines.append("")
    
    lines.append("RISKS:")
    for risk in case.risks:
        lines.append(f"  - {risk.level.value}: {risk.description}")
        lines.append(f"    Mitigation: {risk.mitigation}")
    lines.append("")
    
    lines.append(f"OWNER: {case.owner_department}")
    lines.append(f"SUPPORTING: {', '.join(case.supporting_departments)}")
    lines.append(f"TIMELINE: {case.implementation_weeks} weeks | {case.recommended_quarter}")
    lines.append("")
    lines.append(f"RECOMMENDATION: {case.recommendation}")
    lines.append(f"PRIORITY SCORE: {case.priority_score:.2f}")
    
    return "\n".join(lines)
