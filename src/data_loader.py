"""
LVMH Green in Tech ROI Calculator - Data Loader

This module handles:
- Loading equipment data from Excel file
- Data validation and transformation
- Support for file upload refresh
- Creation of default Excel file from captured data
"""

import pandas as pd
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import io


@dataclass
class EquipmentData:
    """Container for all equipment-related data loaded from Excel."""
    
    # Number of equipment by type
    equipment_counts: Dict[str, int] = field(default_factory=dict)
    
    # Equipment lifespan in months
    equipment_lifespan: Dict[str, int] = field(default_factory=dict)
    
    # Equipment unit prices in euros
    equipment_prices: Dict[str, float] = field(default_factory=dict)
    
    # Consumption parameters
    annual_cloud_consumption: float = 200_000.0
    electricity_price_kwh: float = 0.2016
    screen_power_on_kw: float = 0.16
    screen_power_sleep_kw: float = 0.005


def create_default_excel_data() -> Dict[str, pd.DataFrame]:
    """
    Create default Excel data from the captured image data.
    Returns a dictionary of DataFrames ready to be saved to Excel.
    """
    
    # Number of equipment (from image)
    equipment_counts_data = {
        "Equipement": [
            "Laptop", "Smartphone", "Screen", "Tablet", "Switch/Router",
            "Landline phone", "Refurbished smartphone", "Refurbished screen",
            "Refurbished switch/router", "Meeting room screen"
        ],
        "Current number of equipment": [
            1000, 1000, 600, 100, 100, 500, 100, 250, 300, 200
        ]
    }
    
    # Equipment lifespan in months (from image)
    equipment_lifespan_data = {
        "Equipment": [
            "Laptop", "Smartphone", "Screen", "Tablet", "Switch/Router",
            "Refurbished smartphone", "Refurbished screen", "Refurbished switch/router"
        ],
        "Initial lifespan (months)": [
            60, 48, 72, 60, 72, 36, 72, 84
        ]
    }
    
    # Equipment prices in euros (from image)
    equipment_prices_data = {
        "Equipment": [
            "Laptop", "Smartphone", "Screen", "Tablet", "Landline Phone",
            "Switch/Router", "Refurbished smartphone", "Refurbished screen",
            "Refurbished switch/router"
        ],
        "Unit price": [
            1000, 500, 2000, 500, 350, 250, 1, 800, 100
        ]
    }
    
    # Consumption parameters (from image)
    consumption_data = {
        "Consumption": [
            "Annual cloud consumption",
            "Prix du kWh (euros)",
            "Puissance écran allumé (kW)",
            "Puissance écran en veille (kW)"
        ],
        "Valeur": [
            200000, 0.2016, 0.16, 0.005
        ]
    }
    
    return {
        "Number of equipment": pd.DataFrame(equipment_counts_data),
        "Equipment lifespan": pd.DataFrame(equipment_lifespan_data),
        "Equipment price": pd.DataFrame(equipment_prices_data),
        "Consumption": pd.DataFrame(consumption_data),
    }


def save_default_excel(file_path: Path) -> None:
    """Save default Excel file with all input data."""
    data = create_default_excel_data()
    
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        for sheet_name, df in data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)


def load_excel_data(file_path_or_buffer: Any) -> EquipmentData:
    """
    Load equipment data from Excel file.
    
    Args:
        file_path_or_buffer: Path to Excel file or file-like object (for uploads)
    
    Returns:
        EquipmentData containing all loaded values
    """
    data = EquipmentData()
    
    # Read all sheets
    try:
        sheets = pd.read_excel(file_path_or_buffer, sheet_name=None, engine='openpyxl')
    except Exception as e:
        raise ValueError(f"Failed to read Excel file: {e}")
    
    # Parse Number of equipment
    if "Number of equipment" in sheets:
        df = sheets["Number of equipment"]
        # Handle different column name variants
        equip_col = next((c for c in df.columns if "quip" in c.lower()), df.columns[0])
        count_col = next((c for c in df.columns if "number" in c.lower() or "count" in c.lower()), df.columns[1])
        
        for _, row in df.iterrows():
            equip_name = str(row[equip_col]).strip()
            count = int(row[count_col]) if pd.notna(row[count_col]) else 0
            data.equipment_counts[equip_name] = count
    
    # Parse Equipment lifespan
    if "Equipment lifespan" in sheets:
        df = sheets["Equipment lifespan"]
        equip_col = next((c for c in df.columns if "quip" in c.lower()), df.columns[0])
        lifespan_col = next((c for c in df.columns if "lifespan" in c.lower() or "month" in c.lower()), df.columns[1])
        
        for _, row in df.iterrows():
            equip_name = str(row[equip_col]).strip()
            lifespan = int(row[lifespan_col]) if pd.notna(row[lifespan_col]) else 48
            data.equipment_lifespan[equip_name] = lifespan
    
    # Parse Equipment price
    if "Equipment price" in sheets:
        df = sheets["Equipment price"]
        equip_col = next((c for c in df.columns if "quip" in c.lower()), df.columns[0])
        price_col = next((c for c in df.columns if "price" in c.lower() or "prix" in c.lower()), df.columns[1])
        
        for _, row in df.iterrows():
            equip_name = str(row[equip_col]).strip()
            price = float(row[price_col]) if pd.notna(row[price_col]) else 0.0
            data.equipment_prices[equip_name] = price
    
    # Parse Consumption
    if "Consumption" in sheets:
        df = sheets["Consumption"]
        param_col = df.columns[0]
        value_col = df.columns[1]
        
        for _, row in df.iterrows():
            param_name = str(row[param_col]).strip().lower()
            value = float(row[value_col]) if pd.notna(row[value_col]) else 0.0
            
            if "cloud" in param_name:
                data.annual_cloud_consumption = value
            elif "kwh" in param_name:
                data.electricity_price_kwh = value
            elif "allum" in param_name or "on" in param_name.split():
                data.screen_power_on_kw = value
            elif "veille" in param_name or "sleep" in param_name:
                data.screen_power_sleep_kw = value
    
    # Add missing lifespans with defaults
    _add_missing_lifespans(data)
    
    # Normalize equipment names for consistent lookup
    _normalize_equipment_names(data)
    
    return data


def _add_missing_lifespans(data: EquipmentData) -> None:
    """Add default lifespans for equipment not in the lifespan table."""
    defaults = {
        "Landline phone": 72,
        "Meeting room screen": 72,
    }
    for equip, lifespan in defaults.items():
        if equip not in data.equipment_lifespan:
            data.equipment_lifespan[equip] = lifespan


def _normalize_equipment_names(data: EquipmentData) -> None:
    """Normalize equipment names across all dictionaries for consistent lookup."""
    # Map of common variations to standard names
    name_mapping = {
        "Landline Phone": "Landline phone",
        "landline phone": "Landline phone",
        "Switch/router": "Switch/Router",
        "switch/router": "Switch/Router",
    }
    
    def normalize_dict(d: Dict) -> Dict:
        normalized = {}
        for key, value in d.items():
            normalized_key = name_mapping.get(key, key)
            normalized[normalized_key] = value
        return normalized
    
    data.equipment_counts = normalize_dict(data.equipment_counts)
    data.equipment_lifespan = normalize_dict(data.equipment_lifespan)
    data.equipment_prices = normalize_dict(data.equipment_prices)


def get_equipment_price(data: EquipmentData, equipment: str, 
                        sourcing: str = "new", 
                        dell_new_price: float = 700.0,
                        dell_refurb_price: float = 850.0) -> float:
    """
    Get price for equipment considering sourcing type and Dell contract.
    
    Args:
        data: EquipmentData instance
        equipment: Equipment type name
        sourcing: "new", "refurb", or "lease"
        dell_new_price: Dell contract price for new laptops
        dell_refurb_price: Price for refurbished laptops
    
    Returns:
        Price in euros
    """
    # Special Dell contract pricing for laptops
    if equipment == "Laptop":
        if sourcing == "new":
            return dell_new_price
        elif sourcing == "refurb":
            return dell_refurb_price
        else:  # lease
            return dell_new_price * 0.3  # Approximate annual lease cost
    
    # For refurbished items, look up the refurbished version price
    if sourcing == "refurb":
        refurb_name = f"Refurbished {equipment.lower()}"
        # Check various name formats
        for key in data.equipment_prices:
            if key.lower() == refurb_name.lower():
                return data.equipment_prices[key]
        # Fallback: 50% of new price
        return data.equipment_prices.get(equipment, 0) * 0.5
    
    # For lease, approximate as 30% of new price per year
    if sourcing == "lease":
        return data.equipment_prices.get(equipment, 0) * 0.3
    
    # Default: new price
    return data.equipment_prices.get(equipment, 0)


def get_equipment_lifespan(data: EquipmentData, equipment: str) -> int:
    """Get lifespan in months for equipment, with fallback defaults."""
    if equipment in data.equipment_lifespan:
        return data.equipment_lifespan[equipment]
    
    # Check for refurbished version
    for key in data.equipment_lifespan:
        if equipment.lower() in key.lower():
            return data.equipment_lifespan[key]
    
    # Default lifespan
    return 48  # 4 years default
