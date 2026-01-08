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
    """Generate business case for laptop lifespan extension initiative."""
    
    laptop_count = data.equipment_counts.get("Laptop", 0)
    current_lifespan = data.equipment_lifespan.get("Laptop", 60)
    new_lifespan = int(current_lifespan * (1 + extension_percent))
    extension_months = new_lifespan - current_lifespan
    
    # Calculate devices eligible for upgrade (devices not at end of life)
    eligible_for_upgrade = int(laptop_count * 0.4)  # Assume 40% can be upgraded
    
    # Investment calculation
    upgrade_cost_per_device = 75  # RAM/SSD upgrade
    maintenance_program_cost = 15000
    training_cost = 5000
    total_investment = (eligible_for_upgrade * upgrade_cost_per_device) + maintenance_program_cost + training_cost
    
    # Savings calculation
    current_annual_capex = baseline.capex_annual.get("Laptop", 0)
    new_annual_capex = (laptop_count * params.dell_laptop_new_price) / (new_lifespan / 12)
    annual_savings = current_annual_capex - new_annual_capex
    
    # CO2 calculation
    current_co2 = baseline.co2_embodied_annual.get("Laptop", 0)
    ef_laptop = ADEME_EMISSION_FACTORS.get("Laptop", {}).get("embodied_new", 300)
    new_co2 = (laptop_count * ef_laptop) / (new_lifespan / 12)
    co2_reduction = current_co2 - new_co2
    co2_reduction_pct = co2_reduction / baseline.total_co2 if baseline.total_co2 > 0 else 0
    
    # NPV and payback
    npv = calculate_npv(annual_savings, total_investment)
    payback = (total_investment / annual_savings * 12) if annual_savings > 0 else float('inf')
    
    return BusinessCase(
        initiative_id="I1",
        title="Laptop Lifespan Extension Program",
        category=InitiativeCategory.EQUIPMENT,
        
        scope_summary=f"Extend average laptop lifespan from {current_lifespan} to {new_lifespan} months (+{extension_months} months)",
        target_description=f"Reduce laptop replacement frequency by {extension_percent*100:.0f}% through proactive maintenance and component upgrades",
        affected_equipment={"Laptop": laptop_count},
        
        actions=[
            ActionItem("Audit current laptop fleet age and condition", "IT Asset Management", 2, 0, True),
            ActionItem("Establish partnership with refurbishment vendor", "Procurement", 4, 2000),
            ActionItem("Implement preventive maintenance program", "IT Support", 6, maintenance_program_cost),
            ActionItem(f"Upgrade RAM/SSD on {eligible_for_upgrade} eligible devices", "IT Support", 8, eligible_for_upgrade * upgrade_cost_per_device),
            ActionItem("Update IT replacement policy documentation", "IT Governance", 2, 0),
            ActionItem("Train support staff on extended maintenance", "IT Support", 2, training_cost),
        ],
        prerequisites=[
            "Complete laptop fleet inventory and age analysis",
            "Vendor contract for component supply",
            "Budget approval for upgrade program",
        ],
        
        total_investment=total_investment,
        investment_breakdown={
            f"Component upgrades ({eligible_for_upgrade} devices)": eligible_for_upgrade * upgrade_cost_per_device,
            "Maintenance program setup": maintenance_program_cost,
            "Staff training": training_cost,
            "Vendor partnership setup": 2000,
        },
        
        annual_cost_savings=annual_savings,
        five_year_savings=annual_savings * 5,
        annual_co2_reduction_kg=co2_reduction,
        co2_reduction_percent=co2_reduction_pct,
        payback_months=payback,
        five_year_npv=npv,
        
        risks=[
            RiskItem("Increased support tickets from older devices", RiskLevel.MEDIUM, "Budget 10% additional support FTE"),
            RiskItem("User satisfaction may decrease with older hardware", RiskLevel.LOW, "Prioritize SSD upgrades for performance"),
            RiskItem("Compatibility issues with new software", RiskLevel.LOW, "Maintain minimum spec requirements"),
        ],
        overall_risk=RiskLevel.MEDIUM,
        
        owner_department="IT Procurement",
        supporting_departments=["IT Support", "Finance", "Facilities"],
        implementation_weeks=12,
        recommended_quarter="Q1 2026",
        
        priority_score=0.0,  # Will be calculated
        recommendation="Must Do" if npv > 100000 else "Should Do",
    )


def generate_refurbished_sourcing_business_case(
    data: EquipmentData,
    baseline: BaselineMetrics,
    params: GlobalParameters,
    refurb_share: float = 0.40
) -> BusinessCase:
    """Generate business case for refurbished laptop sourcing initiative."""
    
    laptop_count = data.equipment_counts.get("Laptop", 0)
    lifespan = data.equipment_lifespan.get("Laptop", 60)
    annual_replacements = int(laptop_count / (lifespan / 12))
    refurb_quantity = int(annual_replacements * refurb_share)
    
    # Price difference (Dell contract: new cheaper than refurb, but CO2 benefit)
    new_price = params.dell_laptop_new_price
    refurb_price = params.dell_laptop_refurb_price
    
    # In this case, refurb is MORE expensive, so negative savings
    # But CO2 benefit is significant
    price_diff_per_unit = new_price - refurb_price  # Negative if refurb more expensive
    annual_cost_impact = refurb_quantity * price_diff_per_unit
    
    # CO2 calculation
    ef_new = ADEME_EMISSION_FACTORS.get("Laptop", {}).get("embodied_new", 300)
    ef_refurb = ADEME_EMISSION_FACTORS.get("Laptop", {}).get("embodied_refurb", 50)
    co2_savings_per_device = ef_new - ef_refurb
    annual_co2_reduction = refurb_quantity * co2_savings_per_device
    co2_reduction_pct = annual_co2_reduction / baseline.total_co2 if baseline.total_co2 > 0 else 0
    
    # Investment (process setup, not per-unit)
    setup_investment = 10000  # Procurement process update, vendor qualification
    
    return BusinessCase(
        initiative_id="I2",
        title="Refurbished Laptop Sourcing Strategy",
        category=InitiativeCategory.SOURCING,
        
        scope_summary=f"Source {refurb_share*100:.0f}% of annual laptop replacements ({refurb_quantity} units/year) from refurbished stock",
        target_description="Reduce embodied carbon of laptop fleet while maintaining quality through certified refurbishment",
        affected_equipment={"Laptop": refurb_quantity},
        
        actions=[
            ActionItem("Qualify and certify refurbished laptop vendors", "Procurement", 6, 5000, True),
            ActionItem("Define quality and warranty requirements", "IT Standards", 3, 0, True),
            ActionItem("Update procurement policy and approval workflow", "Procurement", 2, 0),
            ActionItem("Pilot with 50 refurbished units in non-critical roles", "IT", 8, 0),
            ActionItem("Establish returns and warranty process", "Procurement", 3, 2000),
            ActionItem("Full rollout to target departments", "Procurement", 4, 3000),
        ],
        prerequisites=[
            "Vendor qualification criteria defined",
            "Quality assurance process established",
            "User acceptance criteria documented",
        ],
        
        total_investment=setup_investment,
        investment_breakdown={
            "Vendor qualification and audit": 5000,
            "Warranty process setup": 2000,
            "Rollout and communication": 3000,
        },
        
        annual_cost_savings=annual_cost_impact,  # May be negative
        five_year_savings=annual_cost_impact * 5,
        annual_co2_reduction_kg=annual_co2_reduction,
        co2_reduction_percent=co2_reduction_pct,
        payback_months=float('inf') if annual_cost_impact <= 0 else (setup_investment / annual_cost_impact * 12),
        five_year_npv=calculate_npv(annual_cost_impact, setup_investment),
        
        risks=[
            RiskItem("Refurbished units may have higher failure rate", RiskLevel.MEDIUM, "Require minimum 2-year warranty"),
            RiskItem("User perception of 'second-hand' equipment", RiskLevel.LOW, "Communicate sustainability benefits"),
            RiskItem("Supply chain reliability for refurb stock", RiskLevel.MEDIUM, "Qualify multiple vendors"),
        ],
        overall_risk=RiskLevel.MEDIUM,
        
        owner_department="Procurement",
        supporting_departments=["IT", "Sustainability", "Communications"],
        implementation_weeks=16,
        recommended_quarter="Q2 2026",
        
        priority_score=0.0,
        recommendation="Should Do" if annual_co2_reduction > 5000 else "Consider",
    )


def generate_screen_reduction_business_case(
    data: EquipmentData,
    baseline: BaselineMetrics,
    params: GlobalParameters,
    reduction_percent: float = 0.30
) -> BusinessCase:
    """Generate business case for screen count reduction initiative."""
    
    screen_count = data.equipment_counts.get("Screen", 0)
    screens_to_remove = int(screen_count * reduction_percent)
    
    # Calculate savings
    screen_price = data.equipment_prices.get("Screen", 2000)
    screen_lifespan = data.equipment_lifespan.get("Screen", 72)
    annual_capex_savings = (screens_to_remove * screen_price) / (screen_lifespan / 12)
    
    # Energy savings
    annual_kwh_per_screen = (0.16 * 8 + 0.005 * 16) * 365
    energy_savings_kwh = screens_to_remove * annual_kwh_per_screen
    energy_cost_savings = energy_savings_kwh * data.electricity_price_kwh
    
    total_annual_savings = annual_capex_savings + energy_cost_savings
    
    # CO2 calculation
    ef_screen = ADEME_EMISSION_FACTORS.get("Screen", {}).get("embodied_new", 350)
    embodied_co2_reduction = (screens_to_remove * ef_screen) / (screen_lifespan / 12)
    use_phase_co2_reduction = energy_savings_kwh * params.co2_per_kwh
    total_co2_reduction = embodied_co2_reduction + use_phase_co2_reduction
    co2_reduction_pct = total_co2_reduction / baseline.total_co2 if baseline.total_co2 > 0 else 0
    
    # Investment
    hot_desking_investment = 25000  # Furniture, booking system
    communication_cost = 5000
    total_investment = hot_desking_investment + communication_cost
    
    # Detailed breakdown of screen reallocation
    screens_from_hot_desking = int(screens_to_remove * 0.5)
    screens_from_meeting_rooms = int(screens_to_remove * 0.2)
    screens_retired = screens_to_remove - screens_from_hot_desking - screens_from_meeting_rooms
    
    return BusinessCase(
        initiative_id="I3",
        title="Screen Count Optimization Program",
        category=InitiativeCategory.EQUIPMENT,
        
        scope_summary=f"Reduce desktop screen count by {reduction_percent*100:.0f}% ({screens_to_remove} screens) through workspace optimization",
        target_description="Optimize screen allocation through hot-desking, shared workspaces, and meeting room consolidation",
        affected_equipment={"Screen": screens_to_remove},
        
        actions=[
            ActionItem("Conduct workspace utilization audit", "Facilities", 4, 8000, True),
            ActionItem(f"Implement hot-desking for {screens_from_hot_desking} workstations", "Facilities", 8, 15000),
            ActionItem("Deploy desk booking system", "IT", 4, 10000),
            ActionItem(f"Consolidate {screens_from_meeting_rooms} meeting room screens", "Facilities", 4, 0),
            ActionItem(f"Decommission and recycle {screens_retired} underutilized screens", "IT Asset Management", 4, 2000),
            ActionItem("Update clean desk policy", "HR", 2, 0),
            ActionItem("Employee communication and change management", "HR & Comms", 6, 5000),
        ],
        prerequisites=[
            "Workspace utilization data collected (min 4 weeks)",
            "Desk booking solution selected",
            "Change management plan approved",
        ],
        
        total_investment=total_investment + 8000 + 10000,  # Including audit and booking system
        investment_breakdown={
            "Workspace utilization audit": 8000,
            "Hot-desking furniture and setup": 15000,
            "Desk booking system": 10000,
            "Screen decommissioning and recycling": 2000,
            "Change management and communication": 5000,
        },
        
        annual_cost_savings=total_annual_savings,
        five_year_savings=total_annual_savings * 5,
        annual_co2_reduction_kg=total_co2_reduction,
        co2_reduction_percent=co2_reduction_pct,
        payback_months=(total_investment / total_annual_savings * 12) if total_annual_savings > 0 else float('inf'),
        five_year_npv=calculate_npv(total_annual_savings, total_investment),
        
        risks=[
            RiskItem("Employee resistance to hot-desking", RiskLevel.HIGH, "Phased rollout with pilot, gather feedback"),
            RiskItem("Productivity concerns during transition", RiskLevel.MEDIUM, "Provide dual-screen options in focus zones"),
            RiskItem("Meeting room availability issues", RiskLevel.LOW, "Implement room booking optimization"),
        ],
        overall_risk=RiskLevel.HIGH,
        
        owner_department="Facilities",
        supporting_departments=["IT", "HR", "Communications"],
        implementation_weeks=20,
        recommended_quarter="Q1-Q2 2026",
        
        priority_score=0.0,
        recommendation="Must Do" if total_annual_savings > 50000 else "Should Do",
    )


def generate_landline_removal_business_case(
    data: EquipmentData,
    baseline: BaselineMetrics,
    params: GlobalParameters
) -> BusinessCase:
    """Generate business case for landline phone removal initiative."""
    
    landline_count = data.equipment_counts.get("Landline phone", 0)
    
    # Savings calculation
    landline_price = data.equipment_prices.get("Landline phone", 350)
    landline_lifespan = data.equipment_lifespan.get("Landline phone", 72)
    annual_capex_savings = (landline_count * landline_price) / (landline_lifespan / 12)
    
    # Telecom cost savings (assume €15/month/line)
    monthly_telecom_cost = 15
    annual_telecom_savings = landline_count * monthly_telecom_cost * 12
    
    total_annual_savings = annual_capex_savings + annual_telecom_savings
    
    # CO2 calculation
    ef_landline = ADEME_EMISSION_FACTORS.get("Landline phone", {}).get("embodied_new", 25)
    co2_reduction = (landline_count * ef_landline) / (landline_lifespan / 12)
    co2_reduction_pct = co2_reduction / baseline.total_co2 if baseline.total_co2 > 0 else 0
    
    # Investment
    teams_licenses_if_needed = 5000  # Marginal cost for calling features
    headset_cost = landline_count * 30  # Subsidized headsets
    training_cost = 8000
    total_investment = teams_licenses_if_needed + headset_cost + training_cost
    
    # Migration waves
    wave1_count = int(landline_count * 0.3)  # Tech-savvy departments
    wave2_count = int(landline_count * 0.4)  # General office
    wave3_count = landline_count - wave1_count - wave2_count  # Support roles
    
    return BusinessCase(
        initiative_id="I4",
        title="Landline to Teams/VoIP Migration",
        category=InitiativeCategory.INFRASTRUCTURE,
        
        scope_summary=f"Migrate {landline_count} landline phones to Microsoft Teams calling in 3 phases",
        target_description="Complete elimination of physical landline phones by transitioning all voice communications to Teams",
        affected_equipment={"Landline phone": landline_count},
        
        actions=[
            ActionItem("Audit current landline usage patterns", "Telecom", 3, 0, True),
            ActionItem("Verify Teams Phone System licensing", "IT", 2, teams_licenses_if_needed, True),
            ActionItem(f"Wave 1: Migrate {wave1_count} tech-savvy users (IT, Digital)", "Telecom", 4, 0),
            ActionItem(f"Wave 2: Migrate {wave2_count} general office users", "Telecom", 6, 0),
            ActionItem(f"Wave 3: Migrate {wave3_count} remaining users (Support, Reception)", "Telecom", 4, 0),
            ActionItem(f"Distribute {landline_count} headsets for Teams calling", "IT", 4, headset_cost),
            ActionItem("User training on Teams calling features", "IT Training", 6, training_cost),
            ActionItem("Decommission landline infrastructure", "Telecom", 4, 0),
            ActionItem("Terminate telecom contracts", "Procurement", 2, 0),
        ],
        prerequisites=[
            "Microsoft Teams deployed organization-wide",
            "Network bandwidth verified for VoIP",
            "Emergency calling compliance confirmed",
        ],
        
        total_investment=total_investment,
        investment_breakdown={
            "Teams Phone System licensing (marginal)": teams_licenses_if_needed,
            f"Headsets for {landline_count} users": headset_cost,
            "User training program": training_cost,
        },
        
        annual_cost_savings=total_annual_savings,
        five_year_savings=total_annual_savings * 5,
        annual_co2_reduction_kg=co2_reduction,
        co2_reduction_percent=co2_reduction_pct,
        payback_months=(total_investment / total_annual_savings * 12) if total_annual_savings > 0 else float('inf'),
        five_year_npv=calculate_npv(total_annual_savings, total_investment),
        
        risks=[
            RiskItem("Network outages affecting voice", RiskLevel.MEDIUM, "Maintain mobile backup for critical roles"),
            RiskItem("Reception/support desk adaptation", RiskLevel.MEDIUM, "Provide specialized Teams devices"),
            RiskItem("Emergency calling compliance", RiskLevel.LOW, "Configure E911 with Teams"),
        ],
        overall_risk=RiskLevel.MEDIUM,
        
        owner_department="Telecom",
        supporting_departments=["IT", "HR", "Legal"],
        implementation_weeks=16,
        recommended_quarter="Q1-Q2 2026",
        
        priority_score=0.0,
        recommendation="Must Do",
    )


def generate_cloud_finops_business_case(
    data: EquipmentData,
    baseline: BaselineMetrics,
    params: GlobalParameters,
    reduction_percent: float = 0.20
) -> BusinessCase:
    """Generate business case for cloud FinOps initiative."""
    
    current_cloud_cost = baseline.cloud_cost_annual
    target_savings = current_cloud_cost * reduction_percent
    
    # CO2 calculation
    from .config import CLOUD_CO2_FACTORS
    cloud_factor = CLOUD_CO2_FACTORS.get(params.cloud_provider, 0.0004)
    co2_reduction = target_savings * cloud_factor
    co2_reduction_pct = co2_reduction / baseline.total_co2 if baseline.total_co2 > 0 else 0
    
    # Investment
    finops_tool_cost = 15000  # Annual cost for FinOps tooling
    consultant_cost = 30000  # Initial optimization project
    training_cost = 10000
    total_investment = finops_tool_cost + consultant_cost + training_cost
    
    # Breakdown of savings sources
    orphan_resources_savings = target_savings * 0.3
    rightsizing_savings = target_savings * 0.4
    reserved_instances_savings = target_savings * 0.2
    archive_savings = target_savings * 0.1
    
    return BusinessCase(
        initiative_id="I5",
        title="Cloud FinOps and Cost Optimization",
        category=InitiativeCategory.CLOUD,
        
        scope_summary=f"Reduce annual cloud spend by {reduction_percent*100:.0f}% (€{target_savings:,.0f}) through FinOps practices",
        target_description="Implement systematic cloud cost optimization including orphan cleanup, rightsizing, and reserved capacity",
        affected_equipment={},
        
        actions=[
            ActionItem("Deploy FinOps tooling and cost visibility", "Cloud Team", 4, finops_tool_cost, True),
            ActionItem("Conduct cloud cost audit with external consultant", "Cloud Team", 6, consultant_cost, True),
            ActionItem(f"Clean up orphan resources (€{orphan_resources_savings:,.0f} potential)", "Cloud Team", 4, 0),
            ActionItem(f"Implement rightsizing recommendations (€{rightsizing_savings:,.0f} potential)", "Cloud Team", 8, 0),
            ActionItem(f"Purchase reserved instances (€{reserved_instances_savings:,.0f} potential)", "Cloud Team", 4, 0),
            ActionItem(f"Archive cold data to cheaper tiers (€{archive_savings:,.0f} potential)", "Data Team", 6, 0),
            ActionItem("Train teams on FinOps principles", "Cloud Team", 4, training_cost),
            ActionItem("Establish monthly cost review governance", "Cloud Team", 2, 0),
        ],
        prerequisites=[
            "Cloud cost visibility tool deployed",
            "Resource tagging strategy implemented",
            "Cost allocation model defined",
        ],
        
        total_investment=total_investment,
        investment_breakdown={
            "FinOps tooling (annual)": finops_tool_cost,
            "External consultant optimization project": consultant_cost,
            "Team training on FinOps": training_cost,
        },
        
        annual_cost_savings=target_savings,
        five_year_savings=target_savings * 5,
        annual_co2_reduction_kg=co2_reduction,
        co2_reduction_percent=co2_reduction_pct,
        payback_months=(total_investment / target_savings * 12) if target_savings > 0 else float('inf'),
        five_year_npv=calculate_npv(target_savings, total_investment),
        
        risks=[
            RiskItem("Optimization may impact performance", RiskLevel.MEDIUM, "Test changes in staging first"),
            RiskItem("Reserved instance lock-in", RiskLevel.LOW, "Start with 1-year terms, flexible options"),
            RiskItem("Sustaining savings requires ongoing effort", RiskLevel.MEDIUM, "Establish FinOps governance role"),
        ],
        overall_risk=RiskLevel.LOW,
        
        owner_department="Cloud/Infrastructure",
        supporting_departments=["Finance", "Development Teams"],
        implementation_weeks=16,
        recommended_quarter="Q1 2026",
        
        priority_score=0.0,
        recommendation="Must Do",
    )


def generate_onprem_optimization_business_case(
    data: EquipmentData,
    baseline: BaselineMetrics,
    params: GlobalParameters,
    reduction_percent: float = 0.15
) -> BusinessCase:
    """Generate business case for on-premises infrastructure optimization."""
    
    current_onprem_co2 = baseline.onprem_co2_annual
    target_co2_reduction = current_onprem_co2 * reduction_percent
    co2_reduction_pct = target_co2_reduction / baseline.total_co2 if baseline.total_co2 > 0 else 0
    
    # Estimate cost savings from reduced infrastructure
    # Assume on-prem cost is proportional to CO2 (energy-driven)
    estimated_annual_savings = 30000 * reduction_percent  # Rough estimate
    
    # Investment
    audit_cost = 20000
    migration_cost = 40000
    decom_cost = 10000
    total_investment = audit_cost + migration_cost + decom_cost
    
    return BusinessCase(
        initiative_id="I6",
        title="On-Premises Infrastructure Consolidation",
        category=InitiativeCategory.INFRASTRUCTURE,
        
        scope_summary=f"Reduce on-premises infrastructure footprint by {reduction_percent*100:.0f}% through consolidation and cloud migration",
        target_description="Optimize data center presence by retiring legacy systems and consolidating workloads",
        affected_equipment={},
        
        actions=[
            ActionItem("Conduct data center footprint audit", "Infrastructure", 6, audit_cost, True),
            ActionItem("Identify workloads for cloud migration", "Infrastructure", 4, 0),
            ActionItem("Identify servers for consolidation/virtualization", "Infrastructure", 4, 0),
            ActionItem("Execute cloud migration for identified workloads", "Infrastructure", 12, migration_cost),
            ActionItem("Decommission retired infrastructure", "Infrastructure", 4, decom_cost),
            ActionItem("Negotiate reduced colocation/power contracts", "Procurement", 4, 0),
        ],
        prerequisites=[
            "Application portfolio analysis complete",
            "Cloud migration readiness assessment",
            "Business owner sign-off on migrations",
        ],
        
        total_investment=total_investment,
        investment_breakdown={
            "Data center audit": audit_cost,
            "Cloud migration execution": migration_cost,
            "Decommissioning and disposal": decom_cost,
        },
        
        annual_cost_savings=estimated_annual_savings,
        five_year_savings=estimated_annual_savings * 5,
        annual_co2_reduction_kg=target_co2_reduction,
        co2_reduction_percent=co2_reduction_pct,
        payback_months=(total_investment / estimated_annual_savings * 12) if estimated_annual_savings > 0 else float('inf'),
        five_year_npv=calculate_npv(estimated_annual_savings, total_investment),
        
        risks=[
            RiskItem("Application compatibility issues", RiskLevel.MEDIUM, "Thorough testing before migration"),
            RiskItem("Business disruption during migration", RiskLevel.MEDIUM, "Weekend/off-hours execution"),
            RiskItem("Hidden dependencies discovered late", RiskLevel.HIGH, "Comprehensive discovery phase"),
        ],
        overall_risk=RiskLevel.MEDIUM,
        
        owner_department="Infrastructure",
        supporting_departments=["Applications", "Security", "Procurement"],
        implementation_weeks=24,
        recommended_quarter="Q2-Q3 2026",
        
        priority_score=0.0,
        recommendation="Should Do",
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
    
    # Calculate priority scores
    max_savings = max(c.annual_cost_savings for c in cases) if cases else 1
    max_co2 = max(c.annual_co2_reduction_kg for c in cases) if cases else 1
    
    for case in cases:
        savings_score = case.annual_cost_savings / max_savings if max_savings > 0 else 0
        co2_score = case.annual_co2_reduction_kg / max_co2 if max_co2 > 0 else 0
        risk_penalty = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 0.1, RiskLevel.HIGH: 0.2}.get(case.overall_risk, 0)
        
        case.priority_score = (params.alpha * savings_score + (1 - params.alpha) * co2_score) * (1 - risk_penalty)
    
    # Sort by priority
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
