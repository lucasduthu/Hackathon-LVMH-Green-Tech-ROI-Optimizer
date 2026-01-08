# LVMH Green in Tech ROI Calculator
## Complete Technical & User Documentation

---

# Table of Contents

1. [Executive Overview](#executive-overview)
2. [Application Navigation](#application-navigation)
3. [Page-by-Page Guide](#page-by-page-guide)
4. [Data Sources & Inputs](#data-sources--inputs)
5. [Formulas & Calculations](#formulas--calculations)
6. [Business Case Methodology](#business-case-methodology)
7. [Configuration Parameters](#configuration-parameters)

---

# Executive Overview

## Purpose

The LVMH Green in Tech ROI Calculator is a strategic decision-support tool that enables LVMH to:

1. **Quantify the current IT carbon footprint** (baseline analysis)
2. **Model future scenarios** with different Green IT initiatives
3. **Calculate combined ROI** merging financial and environmental returns
4. **Generate actionable business cases** with implementation roadmaps
5. **Optimize initiative portfolios** to maximize Green ROI within budget

## Key Objectives

| Metric | Target | Timeline |
|--------|--------|----------|
| CO₂ Reduction | **-20%** | By 2026 |
| Program Budget | **€500,000** | Annual |
| Maison Coverage | **95%+** | Across LVMH |

## Green ROI Concept

The tool introduces a **unified Green ROI metric** that balances:
- **Financial ROI**: Cost savings from reduced equipment, energy, and cloud spend
- **Environmental ROI**: CO₂ emission reductions (Scope 2 & 3)

**Formula:**
```
Green ROI = α × Normalized(Financial ROI) + (1-α) × Normalized(Environmental ROI)
```
Where α (alpha) is a configurable weight:
- α = 1.0 → Pure financial optimization
- α = 0.5 → Balanced approach (default)
- α = 0.0 → Pure environmental optimization

---

# Application Navigation

## Sidebar

The sidebar provides:

### Navigation Menu
| Page | Purpose |
|------|---------|
| **Overview** | Welcome page with quick start guide |
| **Baseline Analysis** | Current IT footprint and emissions |
| **Scenario Builder** | Configure 2026 scenarios |
| **Scenario Comparison** | Side-by-side analysis with charts |
| **Business Cases** | Detailed implementation plans |
| **Optimization** | Automated scenario optimization |
| **Settings** | Configure emission factors and pricing |

### Data Source
- Upload custom Excel file with equipment data
- Reset to default data

### Global Parameters
- **Program Budget**: Annual investment (default €500,000)
- **Target CO₂ Reduction**: Reduction goal (default 20%)
- **Green ROI Weight (α)**: Balance between financial/environmental (default 0.5)

---

# Page-by-Page Guide

## 1. Overview Page

**Purpose**: Welcome page and quick navigation

**Contents**:
- Key objectives (Target, Budget, Coverage)
- Quick Start buttons for main workflows
- Model assumptions documentation

**Key Actions**: Navigate to Baseline, Scenarios, Business Cases, or Optimization

---

## 2. Baseline Analysis Page

**Purpose**: Understand current IT infrastructure footprint

### Key Performance Indicators

| Metric | Description | Source |
|--------|-------------|--------|
| Total Cost of Ownership | Annual TCO including capex, energy, cloud | Calculated |
| Carbon Footprint | Annual CO₂ (kg) | Calculated |
| Equipment Count | Total devices | Excel input |
| Energy Cost | Annual electricity cost | Calculated |

### Charts

1. **Cost Structure (Pie Chart)**
   - Equipment (Capex)
   - Energy
   - Cloud
   - Program Costs
   - End-of-Life

2. **Emissions Distribution (Pie Chart)**
   - Equipment (Embodied)
   - Equipment (Use Phase)
   - Cloud
   - On-Premises

### Equipment Inventory Table

Displays for each equipment type:
- Count
- Unit Price (€)
- Lifespan (months)
- Annual Capex (€)
- Annual CO₂ (kg)

---

## 3. Scenario Builder Page

**Purpose**: Create and configure 2026 target scenarios

### Scenario Templates

| Template | Description |
|----------|-------------|
| **Moderate Optimization** | Conservative targets: 20% screen reduction, 50% landline, 10% laptop refurb |
| **Aggressive Optimization** | Ambitious targets: 40% screen reduction, 100% landline, 40% laptop refurb |

### Custom Scenario Parameters

#### Device Reductions
| Parameter | Range | Description |
|-----------|-------|-------------|
| Screen Reduction | 0-50% | Reduce screen count through hot-desking |
| Landline Reduction | 0-100% | Migrate to Teams/VoIP |
| Tablet Reduction | 0-50% | Reduce tablet purchases |

#### Sourcing & Lifecycle
| Parameter | Range | Description |
|-----------|-------|-------------|
| Laptop Refurbished Share | 0-80% | % of new laptops sourced refurbished |
| Laptop Lifespan Extension | 0-50% | Extend average laptop life |
| Screen Lifespan Extension | 0-50% | Extend average screen life |

#### Infrastructure Optimization
| Parameter | Range | Description |
|-----------|-------|-------------|
| Cloud Cost Reduction | 0-30% | FinOps savings from cloud |
| Cloud Provider | Azure/AWS/GCP | Affects CO₂ factor |
| On-Prem Reduction | 0-20% | Data center consolidation |

---

## 4. Scenario Comparison Page

**Purpose**: Compare scenarios side-by-side with baseline

### Comparison Table Columns

| Column | Description |
|--------|-------------|
| Scenario | Name of scenario |
| TCO (€) | Total Cost of Ownership |
| Savings (€) | Annual savings vs baseline |
| CO₂ (kg) | Annual emissions |
| CO₂ Reduction (%) | Percentage reduction |
| Financial ROI | Return on investment |
| Payback (years) | Time to recover investment |
| Meets Target | Whether 20% target is met |
| Green ROI | Combined score (0-1) |

### Charts

1. **Cost Comparison (Bar Chart)**: TCO by scenario
2. **Emissions Comparison (Bar Chart)**: CO₂ by scenario with target line

---

## 5. Business Cases Page

**Purpose**: Generate actionable implementation plans

### Executive Summary Metrics

| Metric | Description |
|--------|-------------|
| Total Investment Required | Sum of all initiative investments |
| Annual Savings Potential | Combined annual savings |
| CO₂ Reduction Potential | Total kg CO₂ reduction |
| Priority Initiatives | Number marked "Must Do" |

### Initiative Priority Ranking Table

| Column | Description |
|--------|-------------|
| Rank | Priority order by Green ROI |
| Initiative | Name of the initiative |
| Category | Equipment/Sourcing/Cloud/Infrastructure |
| Investment | Required upfront investment |
| Annual Savings | Yearly cost reduction |
| CO₂ Reduction | Annual kg reduction |
| Payback (months) | Time to ROI |
| Risk | Low/Medium/High |
| Recommendation | Must Do / Should Do / Consider |

### Detailed Business Case Contents

Each business case includes:

#### 1. Scope & Objective
- Clear target description (e.g., "Reduce screen count by 30%")
- Affected equipment and quantities

#### 2. Actions Required
Each action specifies:
- Action description
- Owner department (e.g., IT, Facilities, HR)
- Duration in weeks
- Cost if applicable
- Whether it's a prerequisite

#### 3. Investment Breakdown
Itemized costs for:
- Audits and assessments
- Equipment and setup
- Training
- Change management

#### 4. Returns
- Annual cost savings (€)
- CO₂ reduction (kg/year and %)
- 5-year NPV
- Payback period (months)

#### 5. Risk Assessment
For each risk:
- Risk level (Low/Medium/High)
- Description
- Mitigation strategy

#### 6. Implementation
- Owner department
- Supporting departments
- Timeline (weeks)
- Recommended start quarter

---

## 6. Optimization Page

**Purpose**: Automatically find best initiative combinations

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Max Screen Reduction | 40% | Upper limit for optimization |
| Max Laptop Refurb Share | 60% | Upper limit for refurb share |
| Max Cloud Reduction | 25% | Upper limit for cloud savings |
| Number of Results | 5 | Top N scenarios to show |

### Optimization Results

| Metric | Description |
|--------|-------------|
| Scenarios Evaluated | Total combinations tested |
| Valid Scenarios | Scenarios meeting constraints |
| Best Green ROI | Highest Green ROI score |
| Best CO₂ Reduction | Highest reduction achieved |

### Top Scenarios Output

For each top scenario:
- Financial performance (TCO, savings, ROI, payback)
- Environmental performance (CO₂, reduction %, meets target)
- Key configuration levers used
- Option to add to Scenarios list

---

## 7. Settings Page

**Purpose**: Configure model parameters

### Tab 1: Emission Factors

ADEME-style emission factors per device type:

| Equipment | Factor Type | Unit | Source |
|-----------|-------------|------|--------|
| Laptop | Embodied (New) | kg CO₂e | ADEME |
| Laptop | Embodied (Refurb) | kg CO₂e | ADEME |
| Laptop | Use Phase | kWh/year | Measured |
| Screen | Embodied (New) | kg CO₂e | ADEME |
| Screen | Use Phase | kWh/year | 0.16kW × 8h/day |

**Grid Electricity Factor**: CO₂ per kWh (default 0.052 kg for France)

### Tab 2: Dell Contract

Special pricing under enterprise agreement:

| Item | Default | Note |
|------|---------|------|
| New Laptop | €700 | Below list price due to volume |
| Refurbished Laptop | €850 | Higher than new due to certification |

### Tab 3: Cloud Providers

CO₂ emission factors per € spent:

| Provider | Factor (kg CO₂e/€) |
|----------|-------------------|
| Azure | 0.0004 |
| AWS | 0.0005 |
| GCP | 0.0003 |
| Other | 0.0006 |

---

# Data Sources & Inputs

## Primary Data Source

**File**: `UC1_Inputs-for-ROI-calculation.xlsx`

### Sheet 1: Equipment Counts

| Equipment Type | Count (Default) |
|---------------|-----------------|
| Laptop | 1,000 |
| Smartphone | 1,000 |
| Screen | 600 |
| Tablet | 100 |
| Switch/Router | 100 |
| Landline phone | 500 |
| Refurbished smartphone | 100 |
| Refurbished screen | 250 |
| Refurbished switch/router | 300 |
| Meeting room screen | 200 |

### Sheet 2: Equipment Lifespan

| Equipment | Lifespan (months) |
|-----------|-------------------|
| Laptop | 60 |
| Smartphone | 36 |
| Screen | 72 |
| Tablet | 36 |
| Switch/Router | 60 |
| Landline phone | 72 |

### Sheet 3: Equipment Prices

| Equipment | Unit Price (€) |
|-----------|---------------|
| Laptop | 1,000 |
| Smartphone | 800 |
| Screen | 2,000 |
| Tablet | 600 |
| Switch/Router | 500 |
| Landline phone | 350 |

### Sheet 4: Consumption Parameters

| Parameter | Value |
|-----------|-------|
| Annual Cloud Consumption | €200,000 |
| Annual On-Prem Consumption | €100,000 |
| Electricity Price per kWh | €0.2016 |

---

# Formulas & Calculations

## Baseline Calculations

### 1. Annualized Capex

For each equipment type:
```
Annual_Capex = (Equipment_Count × Unit_Price) / (Lifespan_Months / 12)
```

**Example: Laptops**
```
Annual_Capex = (1,000 × €1,000) / (60 / 12) = €200,000/year
```

### 2. Embodied CO₂ (Annual)

```
Annual_Embodied_CO2 = (Equipment_Count × Emission_Factor) / (Lifespan_Months / 12)
```

**Example: Laptops (New)**
```
Annual_Embodied_CO2 = (1,000 × 300 kg) / 5 years = 60,000 kg/year
```

### 3. Use-Phase Energy (Screens)

```
Annual_kWh = (Power_On × Hours_On + Power_Standby × Hours_Standby) × 365
```

**Example: Screen**
```
Annual_kWh = (0.16 kW × 8h + 0.005 kW × 16h) × 365 = 496 kWh/year
```

### 4. Use-Phase CO₂

```
Use_Phase_CO2 = Annual_kWh × CO2_per_kWh × Equipment_Count
```

### 5. Cloud CO₂

```
Cloud_CO2 = Annual_Cloud_Spend × Cloud_Provider_Factor
```

**Example:**
```
Cloud_CO2 = €200,000 × 0.0004 kg/€ = 80 kg/year
```

### 6. Total Cost of Ownership

```
TCO = Total_Capex + Energy_Cost + Cloud_Cost + OnPrem_Cost + Program_Cost
```

### 7. Total CO₂ Footprint

```
Total_CO2 = Embodied_CO2 + Use_Phase_CO2 + Cloud_CO2 + OnPrem_CO2
```

---

## Scenario Calculations

### 1. Device Reduction Impact

```
New_Count = Original_Count × (1 - Reduction_Percent)
New_Capex = New_Count × Unit_Price / (Lifespan / 12)
```

### 2. Lifespan Extension Impact

```
Extended_Lifespan = Original_Lifespan × (1 + Extension_Percent)
New_Annual_Capex = (Count × Price) / (Extended_Lifespan / 12)
```

### 3. Refurbished Sourcing Impact

Weighted average price:
```
Weighted_Price = (New_Share × New_Price) + (Refurb_Share × Refurb_Price)
```

Weighted embodied CO₂:
```
Weighted_CO2 = (New_Share × New_EF) + (Refurb_Share × Refurb_EF)
```

### 4. Cloud Optimization

```
Optimized_Cloud_Cost = Baseline_Cloud × (1 - Reduction_Percent)
Optimized_Cloud_CO2 = Optimized_Cloud_Cost × Provider_Factor
```

---

## ROI Calculations

### 1. Financial ROI

```
Cost_Savings = Baseline_TCO - Scenario_TCO
Net_Savings = Cost_Savings - Program_Cost
Financial_ROI = Net_Savings / Program_Cost
```

### 2. Payback Period

```
Payback_Years = Program_Cost / Cost_Savings
```

### 3. Environmental ROI

```
CO2_Reduction_Percent = (Baseline_CO2 - Scenario_CO2) / Baseline_CO2
```

### 4. Normalized Scores

For ranking scenarios:
```
Normalized_Financial = (ROI - Min_ROI) / (Max_ROI - Min_ROI)
Normalized_Environmental = CO2_Reduction_Percent / Target_Reduction
```

### 5. Green ROI

```
Green_ROI = α × Normalized_Financial + (1-α) × min(1, Normalized_Environmental)
```

---

## Business Case Calculations

### 1. Net Present Value (NPV)

```
NPV = -Initial_Investment + Σ(Annual_Savings / (1 + r)^t)
```
Where:
- r = discount rate (default 5%)
- t = year (1 to 5)

**Example:**
```
Investment = €50,000
Annual_Savings = €80,000
NPV = -50,000 + 80,000/1.05 + 80,000/1.05² + ... = €296,000
```

### 2. Payback Period

```
Payback_Months = (Investment / Annual_Savings) × 12
```

### 3. Priority Score

```
Priority_Score = (α × Savings_Score + (1-α) × CO2_Score) × (1 - Risk_Penalty)
```

Risk penalties:
- Low: 0%
- Medium: 10%
- High: 20%

---

# Business Case Methodology

## Initiative Coverage

| Initiative | Category | Key Levers |
|------------|----------|------------|
| Screen Count Optimization | Equipment | Hot-desking, workspace audit |
| Laptop Lifespan Extension | Equipment | Maintenance, upgrades |
| Landline to Teams Migration | Infrastructure | VoIP transition |
| Refurbished Laptop Sourcing | Sourcing | Vendor qualification |
| Cloud FinOps | Cloud | Cost optimization |
| On-Prem Consolidation | Infrastructure | Migration, retirement |

## Action Development Methodology

Actions are developed based on:
1. **Prerequisites**: Must-complete items before main actions
2. **Sequential tasks**: Ordered by dependencies
3. **Owner assignment**: Based on RACI matrix
4. **Duration estimation**: Based on complexity and resources
5. **Cost allocation**: Direct costs + overhead

## Risk Assessment Framework

| Level | Criteria | Examples |
|-------|----------|----------|
| **Low** | Minimal disruption, proven approach | Policy updates, training |
| **Medium** | Some change management needed | New processes, minor migrations |
| **High** | Significant organizational change | Hot-desking, major migrations |

---

# Configuration Parameters

## Editable via Settings Page

| Parameter | Location | Default | Impact |
|-----------|----------|---------|--------|
| ADEME Factors | Emission Factors tab | Per equipment | CO₂ calculations |
| CO₂ per kWh | Emission Factors tab | 0.052 kg | Use-phase CO₂ |
| Dell New Price | Dell Contract tab | €700 | Laptop capex |
| Dell Refurb Price | Dell Contract tab | €850 | Refurb capex |
| Cloud Provider | Cloud Providers tab | Azure | Cloud CO₂ factor |

## Editable via Sidebar

| Parameter | Default | Impact |
|-----------|---------|--------|
| Program Budget | €500,000 | ROI calculations |
| Target CO₂ Reduction | 20% | Target compliance |
| Green ROI Weight (α) | 0.5 | Ranking balance |

---

# Persona System & Maison Configuration

## How Personas Impact Computations

The persona system allows different Maisons to model their unique workforce composition and understand its impact on equipment needs and carbon footprint.

### Persona Definitions

| Persona | Laptops | Screens | Smartphones | Description |
|---------|---------|---------|-------------|-------------|
| **Office** | 1 | 1 | 1 | Corporate employees, admin, management, finance |
| **Tech** | 1 | 2 | 1 | Developers, IT, data analysts (need dual screens) |
| **Retail** | 0 | 0 | 1 | Store staff, boutique teams (smartphone-only) |

### Impact on Equipment Calculations

For a Maison with `N` employees and persona distribution `(O%, T%, R%)`:

```
Total_Laptops = N × O% × 1 + N × T% × 1 + N × R% × 0
Total_Screens = N × O% × 1 + N × T% × 2 + N × R% × 0
Total_Smartphones = N × O% × 1 + N × T% × 1 + N × R% × 1
```

### Example: Impact by Maison Type

| Maison Type | Office | Tech | Retail | Laptops | Screens | Smartphones | CO₂ Impact |
|-------------|--------|------|--------|---------|---------|-------------|------------|
| **Louis Vuitton** (Retail-heavy) | 30% | 10% | 60% | 400 | 500 | 1,000 | Lower |
| **Hennessy** (Corporate) | 70% | 15% | 15% | 850 | 1,000 | 1,000 | Medium |
| **Dior Digital** (Tech-heavy) | 40% | 45% | 15% | 850 | 1,300 | 1,000 | Higher |

*Assuming 1,000 employees per Maison*

### Why Tech Personas Have Higher CO₂

The Tech persona requires **2 screens** instead of 1, which significantly impacts:
- **Embodied CO₂**: +350 kg per extra screen
- **Use-phase CO₂**: +496 kWh/year per extra screen
- **Annual cost**: +€2,000/5 years = €400/year per screen

**Calculation example** (1,000 employees, 45% Tech):
- Extra screens: 450
- Extra annual embodied CO₂: 450 × 350 kg / 6 years = **26,250 kg/year**
- Extra annual use-phase CO₂: 450 × 496 kWh × 0.052 kg/kWh = **11,606 kg/year**

### Adjusting for Your Maison

Different LVMH Maisons can adjust their persona distribution in the sidebar or Settings page to reflect their actual workforce:

1. **Retail-Heavy Maisons** (Sephora, Louis Vuitton stores): Higher Retail %
2. **Corporate/Finance Maisons** (Holding company): Higher Office %
3. **Digital/Tech Teams** (LVMH Tech, Digital divisions): Higher Tech %

The model will recalculate all equipment needs and CO₂ projections accordingly.

### Cloud & On-Prem Resource Shares by Persona

Each persona also has different cloud and on-prem resource consumption:

| Persona | Cloud Share | On-Prem Share |
|---------|-------------|---------------|
| Office | 40% | 30% |
| Tech | 60% | 50% |
| Retail | 20% | 10% |

These shares affect the cloud and on-premises CO₂ calculations when optimization scenarios are applied.

---

# Appendix: Default Emission Factors

| Equipment | Embodied New (kg) | Embodied Refurb (kg) | Use Phase (kWh/yr) |
|-----------|-------------------|---------------------|-------------------|
| Laptop | 300 | 50 | 30 |
| Smartphone | 70 | 15 | 5 |
| Screen | 350 | 70 | 496 |
| Tablet | 100 | 20 | 15 |
| Switch/Router | 150 | 30 | 100 |
| Landline phone | 25 | 5 | 10 |

---

*Document Version: 1.1*
*Last Updated: January 2026*
*For LVMH Internal Use*

