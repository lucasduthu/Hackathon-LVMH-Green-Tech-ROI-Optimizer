"""
LVMH Green in Tech ROI Calculator - Optimization Engine

This module provides:
- Grid search for scenario generation
- Constraint-based filtering
- Ranking by Green ROI
- Initiative-level marginal contribution analysis
"""


from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Generator
from itertools import product
import copy

from .data_loader import EquipmentData
from .baseline import BaselineMetrics, compute_baseline
from .scenario import ScenarioParams, ScenarioMetrics, compute_scenario
from .roi import ROIMetrics, compute_all_roi_metrics, rank_scenarios_by_green_roi
from .config import GlobalParameters, DEFAULT_INITIATIVES, Initiative


@dataclass
class OptimizationConfig:
    """Configuration for the optimization search."""
    
    # Budget and targets
    budget: float = 500_000.0
    target_reduction: float = 0.20
    
    # Green ROI weight
    alpha: float = 0.5
    
    # Lever ranges (list of values to try)
    screen_reduction_range: List[float] = None
    landline_reduction_range: List[float] = None
    laptop_lifespan_extension_range: List[float] = None
    laptop_refurb_share_range: List[float] = None
    cloud_reduction_range: List[float] = None
    onprem_reduction_range: List[float] = None
    
    # Limits
    max_scenarios: int = 1000
    top_n: int = 5
    
    def __post_init__(self):
        # Default ranges if not specified
        if self.screen_reduction_range is None:
            self.screen_reduction_range = [0.0, 0.1, 0.2, 0.3, 0.4]
        if self.landline_reduction_range is None:
            self.landline_reduction_range = [0.0, 0.5, 1.0]
        if self.laptop_lifespan_extension_range is None:
            self.laptop_lifespan_extension_range = [0.0, 0.1, 0.2, 0.3]
        if self.laptop_refurb_share_range is None:
            self.laptop_refurb_share_range = [0.0, 0.2, 0.4, 0.6]
        if self.cloud_reduction_range is None:
            self.cloud_reduction_range = [0.0, 0.1, 0.15, 0.2, 0.25]
        if self.onprem_reduction_range is None:
            self.onprem_reduction_range = [0.0, 0.05, 0.1, 0.15]
            
        # Ensure uniqueness and sort
        self.screen_reduction_range = sorted(list(set(self.screen_reduction_range)))
        self.landline_reduction_range = sorted(list(set(self.landline_reduction_range)))
        self.laptop_lifespan_extension_range = sorted(list(set(self.laptop_lifespan_extension_range)))
        self.laptop_refurb_share_range = sorted(list(set(self.laptop_refurb_share_range)))
        self.cloud_reduction_range = sorted(list(set(self.cloud_reduction_range)))
        self.onprem_reduction_range = sorted(list(set(self.onprem_reduction_range)))


@dataclass
class OptimizationResult:
    """Results from optimization run."""
    
    total_scenarios_evaluated: int = 0
    valid_scenarios: int = 0
    top_scenarios: List[Tuple[ScenarioParams, ScenarioMetrics, ROIMetrics]] = None
    
    # Best overall scenario
    best_scenario: Optional[ScenarioParams] = None
    best_metrics: Optional[ScenarioMetrics] = None
    best_roi: Optional[ROIMetrics] = None
    
    # All scenarios (for detailed analysis)
    all_results: List[Tuple[ScenarioParams, ScenarioMetrics, ROIMetrics]] = None


@dataclass
class InitiativeContribution:
    """Marginal contribution of a single initiative."""
    
    initiative: Initiative
    
    # Marginal impacts
    marginal_tco_savings: float = 0.0
    marginal_co2_reduction: float = 0.0
    marginal_co2_reduction_percent: float = 0.0
    
    # ROI metrics
    marginal_roi_financial: float = 0.0
    marginal_green_roi: float = 0.0
    
    # Implementation cost (if separate from program cost)
    implementation_cost: float = 0.0
    
    # Ranking score
    priority_score: float = 0.0


def generate_scenarios_grid(config: OptimizationConfig) -> Generator[ScenarioParams, None, None]:
    """
    Generate candidate scenarios using grid search.
    
    Yields ScenarioParams for each combination of lever values.
    """
    count = 0
    
    # Create all combinations
    for (screen_red, landline_red, laptop_life, laptop_refurb, 
         cloud_red, onprem_red) in product(
        config.screen_reduction_range,
        config.landline_reduction_range,
        config.laptop_lifespan_extension_range,
        config.laptop_refurb_share_range,
        config.cloud_reduction_range,
        config.onprem_reduction_range
    ):
        if count >= config.max_scenarios:
            return
        
        # Create scenario name from parameters
        name = f"Scr-{int(screen_red*100)}%_Land-{int(landline_red*100)}%_LapLife+{int(laptop_life*100)}%_Refurb-{int(laptop_refurb*100)}%"
        
        scenario = ScenarioParams(
            name=name,
            device_reductions={
                "Screen": screen_red,
                "Landline phone": landline_red,
            },
            sourcing_mix={
                "Laptop": {
                    "new": 1.0 - laptop_refurb,
                    "refurb": laptop_refurb,
                    "lease": 0.0
                },
            },
            lifespan_extensions={
                "Laptop": laptop_life,
            },
            cloud_cost_reduction=cloud_red,
            cloud_provider="Azure",  # Could also vary this
            onprem_reduction=onprem_red,
            program_cost=config.budget,
        )
        
        count += 1
        yield scenario


def run_optimization(
    data: EquipmentData,
    params: GlobalParameters,
    config: Optional[OptimizationConfig] = None,
    ademe_factors: Optional[Dict] = None
) -> OptimizationResult:
    """
    Run optimization to find best scenarios.
    
    This implements a grid search over the parameter space,
    evaluates each scenario, filters by constraints, and
    ranks by Green ROI.
    
    Args:
        data: EquipmentData loaded from Excel
        params: GlobalParameters with editable settings
        config: OptimizationConfig controlling the search
        ademe_factors: Optional custom ADEME emission factors
    
    Returns:
        OptimizationResult with top scenarios
    """
    if config is None:
        config = OptimizationConfig()
    
    result = OptimizationResult()
    result.all_results = []
    
    # Compute baseline
    baseline = compute_baseline(data, params, ademe_factors)
    
    # Generate and evaluate all scenarios
    all_scenarios = []
    all_metrics = []
    
    for scenario_params in generate_scenarios_grid(config):
        # Compute scenario metrics
        scenario_metrics = compute_scenario(
            data, baseline, scenario_params, params, ademe_factors
        )
        all_scenarios.append(scenario_params)
        all_metrics.append(scenario_metrics)
    
    result.total_scenarios_evaluated = len(all_scenarios)
    
    if not all_scenarios:
        return result
    
    # Compute ROI metrics for all scenarios
    roi_metrics = compute_all_roi_metrics(
        baseline,
        all_metrics,
        target_reduction=config.target_reduction,
        budget=config.budget,
        alpha=config.alpha
    )
    
    # Combine into results
    for scenario, metrics, roi in zip(all_scenarios, all_metrics, roi_metrics):
        result.all_results.append((scenario, metrics, roi))
    
    # Filter valid scenarios (meet target and budget)
    valid_results = [
        (s, m, r) for s, m, r in result.all_results
        if r.meets_target and r.within_budget
    ]
    result.valid_scenarios = len(valid_results)
    
    # Sort by Green ROI
    sorted_results = sorted(valid_results, key=lambda x: x[2].green_roi, reverse=True)
    
    # Get top N
    result.top_scenarios = sorted_results[:config.top_n]
    
    # Set best scenario
    if result.top_scenarios:
        best = result.top_scenarios[0]
        result.best_scenario = best[0]
        result.best_metrics = best[1]
        result.best_roi = best[2]
    
    return result


def compute_initiative_contributions(
    data: EquipmentData,
    params: GlobalParameters,
    full_scenario: ScenarioParams,
    ademe_factors: Optional[Dict] = None,
    alpha: float = 0.5
) -> List[InitiativeContribution]:
    """
    Compute marginal contribution of each initiative.
    
    For each initiative, compares the full scenario with and without
    that initiative to measure its marginal impact.
    
    Args:
        data: EquipmentData loaded from Excel
        params: GlobalParameters with editable settings
        full_scenario: The complete scenario to analyze
        ademe_factors: Optional custom ADEME emission factors
        alpha: Weight for Green ROI calculation
    
    Returns:
        List of InitiativeContribution sorted by priority score
    """
    baseline = compute_baseline(data, params, ademe_factors)
    full_metrics = compute_scenario(data, baseline, full_scenario, params, ademe_factors)
    
    contributions = []
    
    # Define how each initiative maps to scenario changes
    initiative_mappings = {
        "I1": ("lifespan_extensions", "Laptop", 0.0),  # Laptop lifespan
        "I2": ("sourcing_mix", "Laptop", {"new": 1.0, "refurb": 0.0, "lease": 0.0}),  # Laptop refurb
        "I3": ("device_reductions", "Screen", 0.0),  # Screen reduction
        "I4": ("device_reductions", "Landline phone", 0.0),  # Landline removal
        "I5": ("cloud_cost_reduction", None, 0.0),  # Cloud FinOps
        "I7": ("onprem_reduction", None, 0.0),  # On-prem optimization
    }
    
    for initiative in DEFAULT_INITIATIVES:
        if initiative.id not in initiative_mappings:
            continue
        
        mapping = initiative_mappings[initiative.id]
        field, key, baseline_value = mapping
        
        # Create scenario without this initiative
        scenario_without = copy.deepcopy(full_scenario)
        
        if field == "device_reductions":
            scenario_without.device_reductions[key] = baseline_value
        elif field == "lifespan_extensions":
            scenario_without.lifespan_extensions[key] = baseline_value
        elif field == "sourcing_mix":
            scenario_without.sourcing_mix[key] = baseline_value
        elif field == "cloud_cost_reduction":
            scenario_without.cloud_cost_reduction = baseline_value
        elif field == "onprem_reduction":
            scenario_without.onprem_reduction = baseline_value
        
        # Compute metrics without initiative
        metrics_without = compute_scenario(
            data, baseline, scenario_without, params, ademe_factors
        )
        
        # Compute marginal impacts
        contrib = InitiativeContribution(initiative=initiative)
        
        # TCO savings from this initiative
        contrib.marginal_tco_savings = metrics_without.total_tco - full_metrics.total_tco
        
        # CO₂ reduction from this initiative
        contrib.marginal_co2_reduction = metrics_without.total_co2 - full_metrics.total_co2
        if baseline.total_co2 > 0:
            contrib.marginal_co2_reduction_percent = contrib.marginal_co2_reduction / baseline.total_co2
        
        # Marginal financial ROI
        if params.program_budget > 0:
            contrib.marginal_roi_financial = contrib.marginal_tco_savings / params.program_budget
        
        # Priority score (simple combined metric)
        # Normalize roughly: TCO savings in 10k €, CO₂ in tons
        tco_norm = contrib.marginal_tco_savings / 10_000 if contrib.marginal_tco_savings > 0 else 0
        co2_norm = contrib.marginal_co2_reduction / 1_000 if contrib.marginal_co2_reduction > 0 else 0
        
        contrib.priority_score = alpha * tco_norm + (1 - alpha) * co2_norm
        
        contributions.append(contrib)
    
    # Sort by priority score
    contributions.sort(key=lambda c: c.priority_score, reverse=True)
    
    return contributions


def quick_rank_scenarios(
    data: EquipmentData,
    params: GlobalParameters,
    scenarios: List[ScenarioParams],
    alpha: float = 0.5,
    ademe_factors: Optional[Dict] = None
) -> List[Tuple[ScenarioParams, ScenarioMetrics, ROIMetrics]]:
    """
    Quick ranking of provided scenarios by Green ROI.
    
    Use this for ranking user-defined scenarios without full optimization.
    
    Args:
        data: EquipmentData loaded from Excel
        params: GlobalParameters with editable settings
        scenarios: List of ScenarioParams to evaluate
        alpha: Weight for Green ROI calculation
        ademe_factors: Optional custom ADEME emission factors
    
    Returns:
        List of (scenario, metrics, roi) tuples sorted by Green ROI
    """
    baseline = compute_baseline(data, params, ademe_factors)
    
    all_metrics = []
    for scenario in scenarios:
        metrics = compute_scenario(data, baseline, scenario, params, ademe_factors)
        all_metrics.append(metrics)
    
    roi_list = compute_all_roi_metrics(
        baseline, all_metrics,
        target_reduction=params.target_co2_reduction,
        budget=params.program_budget,
        alpha=alpha
    )
    
    results = list(zip(scenarios, all_metrics, roi_list))
    results.sort(key=lambda x: x[2].green_roi, reverse=True)
    
    return results
