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
