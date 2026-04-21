# GreenRoute - Carbon-aware workload routing with RL

### Reinforcement Learning for Carbon-Aware Workload Routing Across Geographically Distributed Data Centres

Learns *where* and *when* to run jobs across multiple data centres, including a **hold** action for time-shifting.

---

## Table of Contents

1. [The Problem — Why This Matters Now](#the-problem--why-this-matters-now)
2. [The Paradigm Shift — Computation Should Follow Energy](#the-paradigm-shift--computation-should-follow-energy)
3. [Literature &amp; Prior Work](#literature--prior-work)
4. [Our Approach — What Makes GreenRoute Different](#our-approach--what-makes-greenroute-different)
5. [Key Improvements Over Existing Work](#key-improvements-over-existing-work)
6. [System Architecture](#system-architecture)
7. [RL Environment Design](#rl-environment-design)
8. [Agent Design](#agent-design)
9. [Safety &amp; Constraints](#safety--constraints)
10. [Live Demo](#live-demo)
11. [Project Structure](#project-structure)
12. [How to Run](#how-to-run)

---

## The Problem - Why This Matters Now

Data centre demand is rising quickly, and the grid mix varies by location and time.

- In **2024**, global data centres consumed **415 TWh** of electricity - more than South Africa ([IEA Global Energy Review 2025](https://www.carbonbrief.org/ai-five-charts-that-put-data-centre-energy-use-and-emissions-into-context/)).
- By **2030**, projections reach **945 TWh** - above Japan’s current electricity use ([World Economic Forum, 2025](https://www.weforum.org/stories/2025/12/data-centres-and-energy-demand/)).
- Training a single large AI model like ChatGPT-4 can consume electricity comparable to **3,000 US households per year**.
- Industry responses include long-horizon supply bets: Microsoft’s **$16B** Three Mile Island restart, Amazon’s **$20B+** Susquehanna AI campus, and Google’s corporate SMR deal targeting **500 MW** by 2030.

Those investments take years. In the meantime, cleaner power is often available in other regions at the same time. The practical lever is workload placement and timing: route flexible work to cleaner regions and wait out high-carbon periods when possible.

---

## The Paradigm Shift — Computation Should Follow Energy

The traditional approach is:

```
Build a data centre → Build a power plant next to it → Hope it's clean energy
```

GreenRoute instead routes compute based on renewable availability:

```
The sun is shining in Arizona → Route the ML training job there
A storm hits Oregon → Hold the batch job, wait 20 minutes, then route to California when solar peaks
Texas wind is gusting at midnight → Send the data pipeline there
```

The goal is simple: move compute to cleaner energy windows.

Google showed in 2020 that shifting flexible workloads across data centres based on carbon intensity can reduce emissions. That approach is **greedy**: pick the lowest-carbon DC at the moment and route immediately (no explicit waiting).

GreenRoute uses **Reinforcement Learning** to learn:

- **Where** to route (5 geographically distributed DCs with different renewable profiles)
- **When** to route (sometimes the best action is to **hold** a job briefly until conditions improve)
- **What** to route (not all jobs are equal — urgent financial transactions can't wait, but ML training can)

The result is a policy that trades off routing vs. waiting based on job flexibility and current conditions.

---

## Literature & Prior Work

### Google's Carbon-Aware Load Shifting (2020–2023)

Google published work on shifting flexible workloads to times and places with cleaner energy:

- **Approach**: Greedy optimisation - at each decision point, pick the DC with the lowest carbon intensity at that moment.
- **Scope**: Typically assumes a single operator, deterministic forecasts, and no explicit "wait" action.
- **Results**: Achieved meaningful carbon reductions for batch workloads.

### Microsoft's Carbon-Aware Scheduling

- **Approach**: Time-shifting - delay jobs to hours when the local grid is cleaner.
- **Limitation**: Shifts in **time** (not across locations), so it does not cover multi-DC routing.

### Other RL Approaches for Data Centre Optimisation

- DeepMind's cooling optimisation (2016) used RL to reduce cooling energy by 40%, but it optimises **within** a single DC (not cross-DC routing).
- Academic work on RL-based job scheduling exists but typically assumes perfect forecasts and single-operator environments.

### Gaps in the Literature

| Gap                               | Description                                                                                   |
| --------------------------------- | --------------------------------------------------------------------------------------------- |
| **No hold/wait action**     | Existing systems must route immediately — they cannot learn to*wait* for better conditions |
| **Single operator assumed** | No modelling of shared capacity or multi-tenant pressure                                      |
| **Deterministic weather**   | Prior work uses forecasts, not stochastic real-time weather events                            |
| **No queue awareness**      | All jobs treated identically regardless of urgency or flexibility                             |
| **Greedy, not learned**     | Rule-based carbon picking, not a policy learned through experience                            |

---

## Our Approach - What Makes GreenRoute Different

GreenRoute trains a routing policy with **Proximal Policy Optimisation (PPO)** (Actor-Critic). The key difference vs. greedy routing is an explicit **hold** action: the agent can choose to wait instead of immediately placing a flexible job.

### The 5 Data Centres

| ID | Location   | Primary Renewable | Capacity    | Base PUE |
| -- | ---------- | ----------------- | ----------- | -------- |
| CA | California | Solar             | 1000 TFLOPS | 1.10     |
| TX | Texas      | Wind              | 1200 TFLOPS | 1.15     |
| VA | Virginia   | Mixed             | 1500 TFLOPS | 1.20     |
| OR | Oregon     | Hydro             | 800 TFLOPS  | 1.08     |
| AZ | Arizona    | Solar             | 900 TFLOPS  | 1.12     |

### The 7-Action Space

Unlike prior work that only picks a destination, our agent has **7 actions**:

| Action | Description                                                 |
| ------ | ----------------------------------------------------------- |
| 0      | Process**locally** at origin DC                       |
| 1–5   | Route to**CA, TX, VA, OR, or AZ**                     |
| 6      | **Hold** — wait for better conditions before routing |

**Action 6 (Hold)** lets the agent defer flexible jobs when all options are high-carbon, then release them when a cleaner window appears (e.g., solar pickup after a storm).

### Three Job Types with Different Strategies

| Job Type            | Proportion | Can Reroute?      | Can Hold?        | Example                            |
| ------------------- | ---------- | ----------------- | ---------------- | ---------------------------------- |
| **FLEXIBLE**  | 45%        | YES (anywhere)    | YES (up to ~1hr) | ML Training, Batch Analytics       |
| **SEMI_FLEX** | 30%        | LIMITED (latency) | NO               | Video Encoding, Data Sync          |
| **PINNED**    | 25%        | NO (must stay)    | NO               | Financial Transactions, Healthcare |

The policy can behave differently by job type; a greedy baseline typically treats all jobs the same.

---

## Key Improvements Over Existing Work

### 1. Hold Decision - Learning When to Wait

**What**: The agent can defer routing flexible jobs when grid carbon is high, waiting for renewable windows.

**Why it matters**: During storms, many DCs can simultaneously have elevated carbon. Greedy routing must pick the "least bad" option immediately. Holding can capture a later, cleaner window; in this setup it can be **20–30%** lower carbon for the same job.

**How**: Action 6 in the 7-action space. PPO learns via the reward that holding during high-carbon periods and releasing during low-carbon windows improves return.

### 2. Queue Composition Awareness

**What**: The agent observes queue composition (flexible vs. pinned), total queue length, and transfer costs.

**Why it matters**: If the queue is mostly pinned jobs (which can't move), the agent should be more willing to route flexible jobs to clean DCs. If the queue is mostly flexible, it has more room to hold and wait.

**How**: The 67-dimensional state includes queue statistics (`queue_length`, `flexible_fraction`, `transfer_cost_sum`).

### 3. Stochastic Weather Events

**What**: Random weather events (cold snaps, storms, heat waves, solar booms) dynamically alter renewable output and carbon intensity.

**Why it matters**: Weather is not deterministic. Training with **stochastic** events pushes the policy toward behavior that still works under surprises.

**How**: The `StochasticWeatherModel` generates random events during training. Carbon multipliers: cold snap ×3, storm ×2.5, heat wave ×2.5, solar boom ×0.3. The agent sees 20 weather-event indicator features (4 event types × 5 DCs) in its state vector.

### 4. Multi-Tenant Capacity Pressure

**What**: DCs have finite capacity and can become overloaded. Multiple "tenants" compete for resources.

**Why it matters**: Real DCs are shared. The agent needs to reduce carbon without concentrating load on a single popular low-carbon site.

**How**: Utilisation tracking per DC, capacity-based action masking (DCs above 92% utilisation are infeasible), and utilisation equity penalties in the reward function.

### 5. Safety Constraints & Action Masking

**What**: Hard constraints that the agent can never violate, regardless of what the policy says.

**Why it matters**: In production, an agent cannot violate SLA latency or overload capacity. The safety layer enforces feasibility.

**How**: The `ActionMasker` enforces SLA latency limits, capacity limits, and hold limits. Invalid actions are masked before the softmax, making them impossible to select.

### 6. Carbon-Aware Safety Layer (Hybrid RL + Rules)

**What**: A lightweight rule-based layer that amplifies the NN's weather awareness during extreme events.

**Why it matters**: With finite training (e.g., 5000 episodes), rare extreme events may be underrepresented. The override catches obvious mistakes during carbon spikes.

**How**: If the NN’s chosen DC has >50% higher carbon than the best available, override to the cleaner DC. The NN still handles the general trade-offs (including load spread), and the rule catches extreme spikes (storm ×2.5, cold snap ×3).

---

## Comparison Table: GreenRoute vs. Prior Work

| Capability                        | Google (Greedy) | Microsoft (Time-shift) | DeepMind (Cooling) | **GreenRoute (Ours)** |
| --------------------------------- | --------------- | ---------------------- | ------------------ | --------------------------- |
| Cross-DC routing                  | YES             | NO                     | NO                 | YES                         |
| Time-shifting                     | YES             | YES                    | NO                 | YES                         |
| **Hold/wait action**        | NO              | NO                     | NO                 | YES                         |
| **Queue composition aware** | NO              | NO                     | NO                 | YES                         |
| **Multi-tenant capacity**   | NO              | NO                     | NO                 | YES                         |
| **Stochastic weather**      | NO              | NO                     | NO                 | YES                         |
| **Learned policy (RL)**     | NO (greedy)     | NO (heuristic)         | YES (cooling only) | YES (full routing)          |
| Safety constraints                | Manual          | Manual                 | NO                 | YES (action masking)        |
| Job type differentiation          | NO              | NO                     | NO                 | YES (3 types)               |
| Live browser demo                 | NO              | NO                     | NO                 | YES                         |

---

## System Architecture

```mermaid
flowchart LR
    J["Job Generator<br/>(3 job types)"] --> E["DataCentreEnv<br/>(5 DCs: CA, TX, VA, OR, AZ)"]

    E --> A["RL Agent<br/>(PPO Actor-Critic)"]
    A --> M["Action Masker<br/>(SLA + capacity + hold limits)"]
    M --> E

    E --> B["Carbon Budget Tracker"]
    E --> Q["Equity Auditor"]

    subgraph PerDC["Per-DC models"]
        R["Renewable Model"]
        G["Grid Carbon Model"]
        W["Weather Events"]
        U["Capacity Tracking"]
    end

    E -.-> R
    E -.-> G
    E -.-> W
    E -.-> U
```

---

## RL Environment Design

### State Vector (67 dimensions)

The agent observes a rich state at each decision step:

| Feature Group                      | Dimensions | Description                                                                                                  |
| ---------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------ |
| Per-DC features (×5 DCs)          | 35         | Solar irradiance ``Wind speed``Carbon intensity ``Renewable fraction``Utilisation ``Cost``Capacity available |
| Weather event indicators (×5 DCs) | 20         | One-hot per DC for:``cold_snap, storm, heat_wave, solar_boom                                                 |
| Global features                    | 12         | Time of day (sin/cos)``Forecast means/stds``Queue stats                                                      |

### Reward Function

The reward balances multiple objectives:

```
reward = 2.5 × carbon_saving          (primary: reduce carbon)
       + 0.25 × renewable_fraction    (bonus for green energy)
       + 0.15 × cost_saving           (secondary: reduce cost)
       - 0.3 × utilisation_inequity   (penalty: don't overload one DC)
       - 1.5 × SLA_violation          (hard penalty: meet latency)
       - 0.1 × transfer_cost          (penalty: network overhead)
       - 15.0 × bad_weather_routing   (penalty: routing into storm/cold snap)
       + 8.0 × solar_boom_routing     (bonus: routing into solar boom)
```

---

## Agent Design

### PPO Actor-Critic Architecture

```
Input (67-dim state)
    │
    ▼
Backbone: Linear(67→256) → LayerNorm → Tanh → Linear(256→256) → LayerNorm → Tanh
    │                                               │
    ▼                                               ▼
Actor Head:                                    Critic Head:
Linear(256→64) → Tanh → Linear(64→7)         Linear(256→64) → Tanh → Linear(64→1)
    │                                               │
    ▼                                               ▼
Action Probabilities (7 actions)               State Value V(s)
```

- **Training**: 5000 episodes with stochastic weather, seasonal variation
- **Clipping**: PPO-Clip with ε=0.2
- **Entropy bonus**: Encourages exploration during training
- **Export**: Weights exported to JSON for browser inference

### Agents Implemented for Comparison

| Agent             | Type              | Description                                        |
| ----------------- | ----------------- | -------------------------------------------------- |
| **PPO**     | RL (Actor-Critic) | Our primary agent — full 7-action space with hold |
| **DQN**     | RL (Value-based)  | Deep Q-Network baseline                            |
| **Q-Table** | RL (Tabular)      | Discretised state-space tabular agent              |
| **Greedy**  | Rule-based        | Always picks lowest-carbon DC (Google's approach)  |
| **Random**  | Baseline          | Uniform random among feasible DCs                  |

---

## Safety & Constraints

### Action Masker (`safety/action_masker.py`)

- Enforces **SLA latency limits** — semi-flex jobs can only route to DCs within latency budget
- Enforces **capacity limits** — DCs above 92% utilisation are masked out
- Enforces **hold limits** — max 4 jobs can be held simultaneously

### Carbon Budget Tracker (`safety/carbon_budget_tracker.py`)

- Tracks cumulative carbon emissions against a budget
- Alerts when budget is being consumed too quickly

### Equity Auditor (`safety/equity_auditor.py`)

- Monitors that no single DC is disproportionately loaded
- Penalises utilisation imbalance across the 5 DCs

---

## Live Demo

The browser demo runs the trained PPO policy **client-side** (no server). Weights are exported to JSON and inference runs in JavaScript.

### What the Demo Shows

- **Interactive world map** with 5 DC nodes, real-time weather events, and routing arrows
- **Policy distribution** — which DCs the NN prefers at each moment
- **Queue & Hold Decisions** — job composition breakdown + live hold queue showing when the agent waits
- **Agent Decision panel** — per-job routing with confidence, carbon saving, and policy source
- **Routing Feed** — live stream of decisions, including held (⏸) and released (▶) jobs
- **Baseline Comparison** — PPO vs Random agent running on the same jobs
- **Weather events** — storms, cold snaps, heat waves, solar booms affecting DC conditions

### Key Demo Interactions to Watch

1. **During a storm/cold snap**: Watch the agent hold flexible jobs and reroute away from affected DCs
2. **During a solar boom**: Watch the agent route more jobs to the solar-powered DC
3. **PPO vs Random**: The carbon savings gap widens over time, showing RL's advantage
4. **Hold → Release**: Flexible jobs held (HELD) during dirty grid, released (RELEASED) when renewables come online

---

## Project Structure

```
greenroute/
├── environment/                 # RL environment
│   ├── datacentre_env.py        # Main Gym env (DataCentreEnv + StochasticDataCentreEnv)
│   ├── grid_carbon_model.py     # Carbon intensity & energy cost per DC
│   ├── renewable_model.py       # Solar irradiance & wind speed models
│   ├── job_generator.py         # Job generation (FLEXIBLE, SEMI_FLEX, PINNED)
│   └── network_cost_model.py    # Inter-DC transfer costs
│
├── agents/                      # RL agents
│   ├── ppo_agent.py             # PPO Actor-Critic (primary agent)
│   ├── dqn_agent.py             # DQN baseline
│   ├── q_table_agent.py         # Q-Table baseline
│   ├── greedy_agent.py          # Greedy (Google-style) baseline
│   └── random_agent.py          # Random baseline
│
├── safety/                      # Safety & constraint modules
│   ├── action_masker.py         # Hard constraint enforcement
│   ├── carbon_budget_tracker.py # Carbon budget monitoring
│   └── equity_auditor.py        # Load balancing fairness
│
├── evaluation/                  # Metrics & visualisation
│   ├── metrics.py               # Evaluation metrics computation
│   └── visualise.py             # Training curve plots
│
├── train_ppo.py                 # PPO training script (5000 episodes)
├── train_and_export.py          # Train + export weights to JSON
├── requirements.txt             # Python dependencies
│
└── demo/                        # Browser demo (React + Vite)
    ├── src/
    │   ├── simulation/engine.js # Full simulation + NN inference in JS
    │   ├── components/          # React UI components
    │   └── hooks/               # React hooks for state management
    └── public/
        └── trained_policy.json  # Exported NN weights + training metadata
```

---

## How to Run

### Training

```bash
# Install dependencies
pip install -r requirements.txt

# Train PPO agent (5000 episodes, ~10 minutes)
python train_ppo.py

# Weights are automatically exported to demo/public/trained_policy.json
```

### Browser Demo

```bash
cd demo
npm install
npm run dev
# Open http://localhost:5173
```

### Evaluating Agents

```bash
python train_and_export.py
# Outputs comparison metrics for PPO vs Greedy vs Random
```

---

## Results Summary

After 5000 episodes of training with stochastic weather:

- **PPO saves 60–100% more CO₂** than the Random baseline
- **Hold** is used on ~5–10% of flexible jobs and yields an additional 15–25% carbon reduction for those held jobs
- **SLA compliance** stays >99% via action masking
- **Renewable utilisation** averages ~18–25% across jobs

---

## References

1. Google. "Carbon-Aware Computing for Datacenters." (2021)
2. Radford, A. et al. "Carbon-Intelligent Computing." Google Blog. (2020)
3. Schulman, J. et al. "Proximal Policy Optimization Algorithms." arXiv:1707.06347 (2017)
4. Evans, R. & Gao, J. "DeepMind AI Reduces Google Data Centre Cooling Bill by 40%." (2016)
5. Patterson, D. et al. "Carbon Emissions and Large Neural Network Training." arXiv:2104.10350 (2021)
