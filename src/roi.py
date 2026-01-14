"""
LVMH Green in Tech ROI Calculator - ROI Calculations

This module computes ROI metrics:
- Financial ROI and payback period
- Environmental ROI (CO₂ reduction %)
- Combined Green ROI score (normalized weighted sum)
"""

from dataclasses import dataclass
from typing import List, Optional
from .baseline import BaselineMetrics
from .scenario import ScenarioMetrics


@dataclass
class ROIMetrics:
    """Container for all ROI calculation results."""
    
    scenario_name: str = ""
    
    # Financial metrics
    cost_savings: float = 0.0           # TCO_base - TCO_scenario
    roi_financial: float = 0.0          # (savings - program_cost) / program_cost
    payback_years: float = float('inf') # program_cost / annual_savings
    
    # Environmental metrics
    co2_reduction_absolute: float = 0.0  # kg CO₂ reduced
    co2_reduction_percent: float = 0.0   # % reduction from baseline
    meets_target: bool = False           # Meets 20% reduction target?
    
    # Budget compliance
    within_budget: bool = True
    
    # Combined Green ROI (normalized)
    green_roi: float = 0.0
    
    # Normalized scores (for ranking)
    norm_financial: float = 0.0
    norm_environmental: float = 0.0


def compute_financial_roi(
    baseline: BaselineMetrics,
    scenario: ScenarioMetrics
) -> tuple[float, float, float]:
    """
    Compute financial ROI metrics.
    
    Formulas:
    - Operational Savings = Baseline TCO - Scenario Operational TCO
      (Both exclude program investment for fair comparison)
    - ROI = Operational Savings / Program Investment
    - Payback = Program Investment / Operational Savings
    
    Note: Baseline has no program cost (current state before investment).
    Scenario operational_tco also excludes program cost for apples-to-apples comparison.
    
    Returns:
        Tuple of (cost_savings, roi_financial, payback_years)
    """
    # Operational savings: how much running costs are reduced
    # Baseline TCO has no program cost (pre-investment state)
    # Scenario operational_tco excludes program cost (post-investment running costs)
    cost_savings = baseline.total_tco - scenario.operational_tco
    
    # Financial ROI: return on the program investment
    # ROI = savings generated per year / annual investment
    if scenario.program_cost_annual > 0:
        roi_financial = cost_savings / scenario.program_cost_annual
    else:
        roi_financial = float('inf') if cost_savings > 0 else 0.0
    
    # Payback period: how many years to recover the investment
    if cost_savings > 0:
        payback_years = scenario.program_cost_annual / cost_savings
    else:
        # If no savings (or negative), payback is infinite
        payback_years = float('inf')
    
    return cost_savings, roi_financial, payback_years


def compute_environmental_roi(
    baseline: BaselineMetrics,
    scenario: ScenarioMetrics
) -> tuple[float, float]:
    """
    Compute environmental ROI metrics.
    
    Formulas:
    - ΔCO₂ = CO₂_base - CO₂_scenario
    - ReductCO₂ = ΔCO₂ / CO₂_base
    
    Returns:
        Tuple of (co2_reduction_absolute, co2_reduction_percent)
    """
    # CO₂ reduction
    co2_reduction = baseline.total_co2 - scenario.total_co2
    
    # Percentage reduction
    if baseline.total_co2 > 0:
        co2_reduction_percent = co2_reduction / baseline.total_co2
    else:
        co2_reduction_percent = 0.0
    
    return co2_reduction, co2_reduction_percent


def normalize_values(values: List[float]) -> List[float]:
    """
    Normalize values to [0, 1] range using min-max normalization.
    
    Formula: norm = (value - min) / (max - min)
    """
    if not values:
        return []
    
    min_val = min(values)
    max_val = max(values)
    
    if max_val == min_val:
        return [0.5] * len(values)  # All equal, return middle value
    
    return [(v - min_val) / (max_val - min_val) for v in values]


def compute_green_roi(
    norm_financial: float,
    norm_environmental: float,
    alpha: float = 0.5
) -> float:
    """
    Compute combined Green ROI score.
    
    Formula: GreenROI = α × NormFin + (1 - α) × NormEnv
    
    Args:
        norm_financial: Normalized financial ROI (0-1)
        norm_environmental: Normalized environmental ROI (0-1)
        alpha: Weight for financial ROI (0-1)
    
    Returns:
        Green ROI score (0-1)
    """
    return alpha * norm_financial + (1 - alpha) * norm_environmental


def compute_all_roi_metrics(
    baseline: BaselineMetrics,
    scenarios: List[ScenarioMetrics],
    target_reduction: float = 0.20,
    budget: float = 500_000.0,
    alpha: float = 0.5
) -> List[ROIMetrics]:
    """
    Compute all ROI metrics for a list of scenarios.
    
    This includes normalization across all scenarios for Green ROI calculation.
    
    Args:
        baseline: BaselineMetrics for comparison
        scenarios: List of ScenarioMetrics to evaluate
        target_reduction: Target CO₂ reduction (default 20%)
        budget: Program budget constraint
        alpha: Weight for financial ROI in Green ROI
    
    Returns:
        List of ROIMetrics for each scenario
    """
    if not scenarios:
        return []
    
    # First pass: compute individual metrics
    all_metrics = []
    all_roi_financial = []
    all_co2_reduction_percent = []
    
    for scenario in scenarios:
        metrics = ROIMetrics()
        metrics.scenario_name = scenario.scenario_name
        
        # Financial ROI
        savings, roi_fin, payback = compute_financial_roi(baseline, scenario)
        metrics.cost_savings = savings
        metrics.roi_financial = roi_fin
        metrics.payback_years = payback
        
        # Environmental ROI
        co2_abs, co2_pct = compute_environmental_roi(baseline, scenario)
        metrics.co2_reduction_absolute = co2_abs
        metrics.co2_reduction_percent = co2_pct
        
        # Target check
        metrics.meets_target = co2_pct >= target_reduction
        
        # Budget check
        metrics.within_budget = scenario.program_cost_annual <= budget
        
        all_metrics.append(metrics)
        all_roi_financial.append(roi_fin if roi_fin != float('inf') else 0)
        all_co2_reduction_percent.append(co2_pct)
    
    # Second pass: normalize and compute Green ROI
    norm_fin_values = normalize_values(all_roi_financial)
    norm_env_values = normalize_values(all_co2_reduction_percent)
    
    for i, metrics in enumerate(all_metrics):
        metrics.norm_financial = norm_fin_values[i]
        metrics.norm_environmental = norm_env_values[i]
        metrics.green_roi = compute_green_roi(
            metrics.norm_financial,
            metrics.norm_environmental,
            alpha
        )
    
    return all_metrics


def rank_scenarios_by_green_roi(
    roi_metrics: List[ROIMetrics],
    filter_valid_only: bool = True
) -> List[ROIMetrics]:
    """
    Rank scenarios by Green ROI score.
    
    Args:
        roi_metrics: List of ROIMetrics to rank
        filter_valid_only: If True, only include scenarios meeting target and budget
    
    Returns:
        Sorted list of ROIMetrics (highest Green ROI first)
    """
    if filter_valid_only:
        valid = [m for m in roi_metrics if m.meets_target and m.within_budget]
    else:
        valid = roi_metrics
    
    return sorted(valid, key=lambda m: m.green_roi, reverse=True)


def get_top_scenarios(
    roi_metrics: List[ROIMetrics],
    n: int = 5,
    filter_valid_only: bool = True
) -> List[ROIMetrics]:
    """Get top N scenarios by Green ROI."""
    ranked = rank_scenarios_by_green_roi(roi_metrics, filter_valid_only)
    return ranked[:n]
