# SEC Registered Investment Adviser Monitor — Project Plan

## Overview

A web application to track month-over-month changes in SEC-registered investment advisers and exempt reporting advisers, with a subsequent phase adding predictive analytics for upgrade/downgrade risk forecasting.

**Data source:** [SEC Form ADV Data](https://www.sec.gov/data-research/sec-markets-data/information-about-registered-investment-advisers-exempt-reporting-advisers)

---

## Data Overview

| Property | Detail |
|---|---|
| Source | SEC Investment Adviser Registration Depository (IARD) via FINRA |
| Format | CSV/ZIP downloaded monthly from IAPD |
| Coverage | 41,000+ firms, 380,000+ individual advisers |
| History | January 2001 – present |
| Key fields | AUM, employee count, firm type, registration status, control persons, custodians, private funds |

### Relevant Form ADV Sections
- **Item 1** — Identifying info (CRD, name, address, CIK)
- **Item 2** — SEC registration status (registered / exempt reporting)
- **Item 5** — Advisory business: AUM, number of clients, employees
- **Item 6** — Other business activities
- **Item 7** — Financial industry affiliations
- **Item 10** — Control persons
- **Item 11** — Disclosure events (disciplinary history)

---

## Phase 1 — Exploratory Dashboard (Month-over-Month)

### Goals
- Ingest and normalize monthly IAPD CSV snapshots
- Detect and display changes between periods for any registered adviser
- Provide filterable, searchable dashboard UI

### Milestones

#### M1.1 — Data Pipeline
- [ ] Download and parse monthly IAPD CSV/ZIP files from the SEC IAPD bulk data page
- [ ] Design a normalized relational schema (PostgreSQL or SQLite) with a snapshot-per-period model
- [ ] Build an ETL script to diff consecutive monthly snapshots and write a `changes` table
- [ ] Automate monthly ingestion via scheduled job (cron / Celery beat, runs on the 1st of each month)

**Key schema tables:**
```
advisers          (crd, name, registration_type, status, ...)
snapshots         (adviser_crd, period, aum, employees, num_clients, ...)
changes           (adviser_crd, period_from, period_to, field, old_value, new_value)
```

#### M1.2 — Backend API
- [ ] REST API (Python/FastAPI or Node/Express)
- [ ] Endpoints:
  - `GET /advisers` — search/filter list
  - `GET /advisers/{crd}` — adviser profile
  - `GET /advisers/{crd}/history` — all snapshots
  - `GET /advisers/{crd}/changes` — change log
  - `GET /changes?period=YYYY-MM` — all changes in a period

#### M1.3 — Frontend Dashboard
- [ ] Framework: React + TypeScript
- [ ] Views:
  - **Market overview** — aggregate stats (total AUM, registrant count, new/terminated advisers per month)
  - **Adviser search** — filter by name, state, AUM range, registration type
  - **Adviser detail** — profile card, historical AUM chart, change timeline
  - **Change feed** — recent notable changes across all advisers (sortable by AUM delta, employee change, status change)
- [ ] Charting: Recharts or Chart.js (AUM trend, employee trend)

#### M1.4 — Deployment (Phase 1)
- [ ] Containerize with Docker (API + frontend + DB)
- [ ] Deploy to a cloud provider (AWS/GCP/Azure) or self-hosted
- [ ] Basic auth / login for access control

---

## Phase 2 — Predictive Analytics (Upgrade/Downgrade Risk)

### Goals
- Predict which advisers are at risk of downgrading registration status (SEC → state, or termination) or upgrading (state → SEC)
- Surface risk scores in the dashboard

### Risk Factors (Features)
| Signal | Description |
|---|---|
| AUM trajectory | Significant drop approaching $100M SEC threshold |
| Employee decline | Reduction in headcount over 3–6 months |
| Client count change | Loss of clients |
| Disclosure events | New disciplinary disclosures (Item 11) |
| Ownership changes | Control person turnover (Item 10) |
| Business activity shift | Change in primary advisory activities |
| AUM per employee | Efficiency ratio trend |

### Milestones

#### M2.1 — Feature Engineering
- [ ] Build a time-series feature store from the `snapshots` table
- [ ] Compute derived signals: month-over-month % change in AUM, rolling averages (3-month, 6-month), threshold proximity
- [ ] Label historical data: find advisers who actually upgraded/downgraded (ground truth)

#### M2.2 — Model Development
- [ ] Baseline: logistic regression on AUM delta + employee delta
- [ ] Improved: gradient boosting (XGBoost / LightGBM) with full feature set
- [ ] Evaluation: precision/recall on held-out periods, handle class imbalance
- [ ] Explainability: SHAP values to show top contributing factors per adviser

#### M2.3 — API Integration
- [ ] `GET /advisers/{crd}/risk` — returns risk score + contributing factors
- [ ] `GET /advisers/at-risk?threshold=0.7` — list of high-risk advisers

#### M2.4 — Dashboard Integration
- [ ] Risk score badge on adviser cards
- [ ] "At Risk" watchlist view
- [ ] Factor breakdown chart (SHAP waterfall) per adviser

---

## Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Data ingestion | Python (pandas, requests) | Best ecosystem for SEC CSV parsing |
| Database | PostgreSQL | Handles time-series snapshots well |
| Backend API | Python / FastAPI | Consistent with data pipeline language |
| Frontend | React + TypeScript | Component reuse, typed props |
| Charts | Recharts | React-native, easy time-series |
| ML | scikit-learn + XGBoost | Standard, explainable |
| Explainability | SHAP | Industry standard for feature attribution |
| Containerization | Docker + Docker Compose | Reproducible local + cloud deploy |
| Scheduling | cron / Celery beat | Monthly IAPD download + ETL on 1st of month |

---

## Data Ingestion Strategy

```
IAPD bulk CSV/ZIP download (monthly, ~1st of month)
        │
        ▼
Parse CSV → normalize fields → load into `snapshots` table (keyed by YYYY-MM)
        │
        ▼
Diff engine: compare snapshot(T) vs snapshot(T-1 month)
        │
        ▼
Write to `changes` table
        │
        ▼
API serves dashboard + ML model reads features
```

**IAPD download URL pattern:**
`https://www.sec.gov/data-research/sec-markets-data/information-about-registered-investment-advisers-exempt-reporting-advisers`
- Files are posted as ZIP archives; filename encodes the snapshot date.
- Download script should check for a new file each month and skip if already ingested (idempotent).

**Key SEC threshold to watch:** $100M AUM — below this, advisers typically must withdraw SEC registration and register at the state level. This is the primary driver of forced downgrades.

---

## Open Questions / Decisions Needed

1. ~~**Update frequency:** Quarterly SEC snapshots vs. daily IAPD scraping~~ — **decided: monthly IAPD bulk download**
2. **Scope:** SEC-registered only, or include state-registered and exempt reporting advisers?
3. **User access:** Internal tool or public-facing? Drives auth requirements.
4. **Cloud vs. self-hosted:** Affects infrastructure choices.
5. **IAPD file availability:** Confirm the SEC posts a fresh bulk ZIP each month and document the expected release cadence (typically mid-month for prior month data).

---

## Phase 1 Deliverables Checklist

- [ ] ETL pipeline running against monthly IAPD bulk data
- [ ] PostgreSQL schema with snapshot + change tables
- [ ] FastAPI backend with core endpoints
- [ ] React dashboard: search, adviser detail, change feed
- [ ] Dockerized deployment
- [ ] Basic documentation

## Phase 2 Deliverables Checklist

- [ ] Feature engineering pipeline
- [ ] Trained classification model with evaluation report
- [ ] Risk score API endpoints
- [ ] Dashboard risk views and watchlist
- [ ] Model retraining schedule (monthly, triggered after ETL completes)
