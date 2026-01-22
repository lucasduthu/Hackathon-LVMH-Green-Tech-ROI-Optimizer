"""
LVMH Green in Tech ROI Calculator - Configuration and Constants

This module contains:
- ADEME emission factors (placeholders, editable in UI)
- Default global parameters
- Equipment and persona definitions

Note: ADEME factors are approximate values based on public data.
Users can edit these in the application UI or load from external file.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

# =============================================================================
# ADEME EMISSION FACTORS (Placeholder values - editable in UI)
# =============================================================================
# Source: Based on ADEME Base Carbone public data (approximate values)
# Units: kg CO₂e per device (embodied emissions)

ADEME_EMISSION_FACTORS: Dict[str, Dict[str, float]] = {
    # Standard devices - new equipment embodied emissions
    "Laptop": {
        "embodied_new": 300.0,       # kg CO₂e for new laptop
        "embodied_refurb": 50.0,     # kg CO₂e for refurbished (mostly logistics)
        "embodied_lease": 300.0,     # Same as new for lease
        "use_phase_kwh_year": 50.0,  # kWh/year in use phase
    },
    "Smartphone": {
        "embodied_new": 70.0,
        "embodied_refurb": 10.0,
        "embodied_lease": 70.0,
        "use_phase_kwh_year": 5.0,
    },
    "Screen": {
        "embodied_new": 350.0,
        "embodied_refurb": 60.0,
        "embodied_lease": 350.0,
        "use_phase_kwh_year": None,  # Calculated dynamically from power consumption
    },
    "Tablet": {
        "embodied_new": 100.0,
        "embodied_refurb": 15.0,
        "embodied_lease": 100.0,
        "use_phase_kwh_year": 15.0,
    },
    "Switch/Router": {
        "embodied_new": 80.0,
        "embodied_refurb": 15.0,
        "embodied_lease": 80.0,
        "use_phase_kwh_year": 100.0,  # Always-on networking equipment
    },
    "Landline phone": {
        "embodied_new": 25.0,
        "embodied_refurb": 5.0,
        "embodied_lease": 25.0,
        "use_phase_kwh_year": 10.0,
    },
    "Meeting room screen": {
        "embodied_new": 500.0,
        "embodied_refurb": 80.0,
        "embodied_lease": 500.0,
        "use_phase_kwh_year": 200.0,  # Larger screens, more usage
    },
    # Refurbished versions (for stock tracking)
    "Refurbished smartphone": {
        "embodied_new": 10.0,  # Already refurbished
        "embodied_refurb": 10.0,
        "embodied_lease": 10.0,
        "use_phase_kwh_year": 5.0,
    },
    "Refurbished screen": {
        "embodied_new": 60.0,
        "embodied_refurb": 60.0,
        "embodied_lease": 60.0,
        "use_phase_kwh_year": None,
    },
    "Refurbished switch/router": {
        "embodied_new": 15.0,
        "embodied_refurb": 15.0,
        "embodied_lease": 15.0,
        "use_phase_kwh_year": 100.0,
    },
}

# =============================================================================
# ELECTRICITY EMISSION FACTORS
# =============================================================================
# French electricity grid is relatively clean due to nuclear
# Source: ADEME Base Carbone - France average

ELECTRICITY_CO2_PER_KWH = 0.052  # kg CO₂e per kWh (French grid average)

# =============================================================================
# CLOUD PROVIDER EMISSION FACTORS
# =============================================================================
# Approximate kg CO₂e per euro spent on cloud services
# These vary significantly based on region and workload type

CLOUD_CO2_FACTORS: Dict[str, float] = {
    "Azure": 0.0004,      # Microsoft Azure (global average)
    "GCP": 0.0003,        # Google Cloud (more renewable energy)
    "AWS": 0.00035,       # Amazon Web Services
    "Alternative": 0.0002, # Greener European providers
}

# =============================================================================
# DELL CONTRACT PRICING
# =============================================================================

DELL_CONTRACT_PRICES: Dict[str, Dict[str, float]] = {
    "new": {
        "standard": 700.0,
        "performance": 1000.0,
        "premium": 1400.0,
    },
    "refurbished": {
        "standard": 450.0,
        "performance": 650.0,
    },
    "lease": {
        "monthly": 35.0,
    },
}

# =============================================================================
# DEFAULT GLOBAL PARAMETERS
# =============================================================================

@dataclass
class GlobalParameters:
    """Global parameters for the ROI calculator, all editable in UI."""
    
    # Program parameters
    program_budget: float = 500_000.0  # € per year
    target_co2_reduction: float = 0.20  # 20% reduction target by 2026
    end_of_life_cost: float = 5_000.0  # € per year for disposal partner
    
    # Screen usage parameters
    screen_hours_on: float = 8.0       # Hours per day screen is active
    screen_hours_sleep: float = 16.0   # Hours per day screen in sleep mode
    
    # Green ROI weighting
    alpha: float = 0.5  # Weight for financial ROI in combined Green ROI score
    
    # Dell contract special pricing (override Excel values for laptops)
    dell_laptop_new_price: float = 700.0     # € - Dell contract price for new
    dell_laptop_refurb_price: float = 850.0  # € - Refurbished laptop price
    
    # Emission factors (can be overridden)
    co2_per_kwh: float = ELECTRICITY_CO2_PER_KWH
    cloud_provider: str = "Azure"
    
    # =========================================================================
    # BUSINESS CASE ASSUMPTIONS (Industry benchmarks as defaults)
    # =========================================================================
    
    # Laptop Lifespan Extension (I1)
    laptop_upgrade_cost_per_unit: float = 75.0  # € per device (RAM/SSD upgrade)
    laptop_eligible_upgrade_percent: float = 0.40  # 40% of fleet eligible
    
    # Refurbished Sourcing (I2)
    refurb_share_percent: float = 0.40  # 40% of replacements from refurbished
    refurb_setup_investment: float = 0.0  # € - minimal/zero if using same Dell contract
    
    # Screen Reduction (I3)
    screen_hot_desking_investment: float = 25_000.0  # € furniture/booking system
    screen_communication_cost: float = 5_000.0  # € change management
    screen_audit_cost: float = 8_000.0  # € utilization audit
    screen_booking_system_cost: float = 10_000.0  # € desk booking system
    
    # Landline Removal (I4)
    landline_monthly_telecom_cost: float = 15.0  # € per line per month
    landline_teams_license_cost: float = 5_000.0  # € marginal Teams licensing
    landline_headset_cost_per_unit: float = 30.0  # € per headset
    landline_training_cost: float = 8_000.0  # € training program
    
    # Cloud FinOps (I5) - Granular Strategy Inputs
    # Investment costs
    cloud_finops_tool_cost: float = 15_000.0  # € annual tooling (e.g., CloudHealth, Spot.io)
    cloud_consultant_cost: float = 20_000.0  # € optimization project / consultant
    cloud_training_cost: float = 5_000.0     # € team training on FinOps practices
    
    # Cloud Cost Breakdown (must sum to 100%)
    cloud_compute_share: float = 0.60        # % of cloud bill that is compute (VMs, containers)
    cloud_storage_share: float = 0.25        # % of cloud bill that is storage (S3, disks, DBs)
    cloud_other_share: float = 0.15          # % of cloud bill that is other (network, transfer)
    
    # Strategy 1: Rightsizing — applies to COMPUTE portion only
    finops_rightsizing_vm_share: float = 0.30    # % of compute to analyze for rightsizing
    finops_rightsizing_savings: float = 0.20     # % savings on resized VMs (industry: 15-25%)
    
    # Strategy 2: Reserved Instances — applies to COMPUTE portion only
    finops_reserved_workload_share: float = 0.40 # % of compute suitable for commitment
    finops_reserved_discount: float = 0.35       # % discount for Reserved/Savings Plans (30-60%)
    
    # Strategy 3: Orphan Cleanup — applies to TOTAL spend
    finops_orphan_waste_percent: float = 0.08    # % of total spend that is orphaned (5-15%)
    
    # Strategy 4: Scheduling — applies to COMPUTE portion only
    finops_dev_test_share: float = 0.25          # % of compute that is dev/test environments
    finops_scheduling_savings: float = 0.50      # % of time dev/test can be off (nights/weekends)
    
    # Strategy 5: Storage Tiering — applies to STORAGE portion only
    finops_archivable_data: float = 0.40         # % of storage that can be archived
    finops_archive_discount: float = 0.70        # % savings from archiving (S3 Glacier vs Standard)
    
    # On-Prem Consolidation (I6)
    onprem_annual_infra_cost: float = 100_000.0  # € estimated annual on-prem infrastructure cost
    onprem_reduction_target: float = 0.15        # % reduction target (10-25% typical)
    onprem_audit_cost: float = 20_000.0  # € data center audit
    onprem_migration_cost: float = 40_000.0  # € cloud migration
    onprem_decom_cost: float = 10_000.0  # € decommissioning

# =============================================================================
# PERSONA DEFINITIONS
# =============================================================================

DEFAULT_PERSONAS: Dict[str, Dict[str, int]] = {
    "Office": {
        "Laptop": 1,
        "Screen": 1,
        "Smartphone": 1,
        "Landline phone": 0,  # Migrating to Teams/VoIP by 2026
    },
    "Retail": {
        "Smartphone": 1,  # Store staff (e.g., Sephora)
    },
    "Tech": {
        "Laptop": 1,
        "Screen": 2,      # Power users need dual screens
        "Smartphone": 1,
    },
}

# Cloud and on-prem resource shares per persona (fractions)
PERSONA_RESOURCE_SHARES: Dict[str, Dict[str, float]] = {
    "Office": {
        "cloud_share": 0.4,
        "onprem_share": 0.3,
    },
    "Retail": {
        "cloud_share": 0.2,
        "onprem_share": 0.1,
    },
    "Tech": {
        "cloud_share": 0.6,
        "onprem_share": 0.5,
    },
}

# =============================================================================
# INITIATIVE DEFINITIONS
# =============================================================================

@dataclass
class Initiative:
    """Represents a Green IT initiative with its parameters."""
    id: str
    name: str
    description: str
    category: str  # "equipment", "sourcing", "cloud", "onprem", "behavior"
    default_enabled: bool = False

DEFAULT_INITIATIVES = [
    Initiative("I1", "Extend Laptop Lifespan", 
               "Extend laptop lifespan by 12+ months through refurbishment", "equipment"),
    Initiative("I2", "Increase Refurbished Laptops", 
               "Replace 30% of new laptop purchases with refurbished", "sourcing"),
    Initiative("I3", "Reduce Screen Count", 
               "Reduce desktop screens by 20% through shared workspaces", "equipment"),
    Initiative("I4", "Remove Landlines", 
               "Migrate 100% of landline phones to Teams/VoIP", "equipment"),
    Initiative("I5", "Cloud FinOps", 
               "Reduce cloud spend by 15% through optimization", "cloud"),
    Initiative("I6", "Switch Cloud Provider", 
               "Switch to greener cloud provider (lower CO₂/€)", "cloud"),
    Initiative("I7", "On-Prem Optimization", 
               "Reduce on-prem infrastructure by 10%", "onprem"),
    Initiative("I8", "Power Management", 
               "Implement aggressive sleep mode policies for screens", "behavior"),
]

# =============================================================================
# EQUIPMENT TYPE MAPPINGS
# =============================================================================

# Map standard equipment to their refurbished counterparts
REFURBISHED_MAPPING = {
    "Smartphone": "Refurbished smartphone",
    "Screen": "Refurbished screen",
    "Switch/Router": "Refurbished switch/router",
}

# Equipment types that are screens (for energy calculations)
SCREEN_TYPES = ["Screen", "Refurbished screen", "Meeting room screen"]

# Equipment types that can use Dell pricing override
DELL_EQUIPMENT = ["Laptop"]
