# LVMH Green in Tech ROI Calculator

A strategic decision-support tool helping LVMH evaluate, compare, and prioritize Green IT initiatives by combining financial ROI with environmental impact assessment.

## Quick Start for Team

### Prerequisites
- Python 3.8 or higher installed
- Internet connection (for installing dependencies)

### 1. Installation

Clone this repository or download the ZIP file:

```bash
git clone <your-repo-url>
cd lvmh-green-roi-calculator
```

Install the required packages:

```bash
pip install -r requirements.txt
```

### 2. Running the App

Run the application using Streamlit:

```bash
streamlit run app.py
```

The app will open automatically in your browser at **http://localhost:8501**.

---

## Project Structure

- **`app.py`**: Main application entry point
- **`src/`**: Calculation modules (Baseline, Scenarios, Optimization, ROI)
- **`data/`**: Equipment data (Excel files)
- **`assets/`**: LVMH-branded styling (CSS)
- **`docs/`**: Detailed documentation

## The decision journey

The app is organised as a five-step *parcours de décision*, with a persistent
**Green ROI arbitrage gauge** (`Green ROI = α · Finance + (1 − α) · Carbone`) that
reacts live to every adjustment:

1. **Cadrer** — frame the Maison: pick a preset or set headcount and the
   Office / Tech / Retail persona split; the target inventory and budget update instantly.
2. **Diagnostiquer** — the reference situation: TCO and carbon KPIs, cost &
   emissions breakdowns, and the detailed equipment inventory.
3. **Explorer** — build scenarios manually (four levers) or let the optimiser
   sweep ~4 800 configurations and surface a diverse, constraint-compliant Top 5.
4. **Arbitrer** — compare on the Green ROI frontier (savings × CO₂ reduction),
   read the recommendation, and review the side-by-side table.
5. **Planifier** — turn the decision into a 2026 roadmap: deployment gantt,
   gain/risk prioritisation, and COMEX-ready project sheets.

Every figure is computed by the engine in `src/` — baseline, scenarios, ROI,
optimiser and business cases. Use the sidebar **Réglages & facteurs** to tune the
carbon target and on-prem baseline, **Exporter le dossier** for a Markdown summary,
and **Mode expert** to view all five phases at once.

---

*Prepared for LVMH Group IT Department*
