---
name: orbital-compute-decision-engine
description: >-
  Provides end-to-end procedures, algorithms, simulation setups, and research methodology for solving IASTAM 6.0 Track 1 Problem 1: "Process or Transmit?". Use this skill whenever building or running orbital edge simulators, designing decision engines (MDP, RL, heuristics, Lyapunov optimization), benchmarking policies, or writing the IEEE research paper.
---

# Orbital Compute Decision Engine: Problem 1 ("Process or Transmit?")

This skill provides step-by-step instructions, mathematical definitions, architectural guidelines, and evaluation workflows to develop a winning solution for **Track 1, Problem 1: Process or Transmit?** in the **IEEE IASTAM 6.0 Technical Challenge** (organized with TUNSA).

---

## 1. Quick Reference & Context Links

- **Problem Statement:** How can a LEO satellite automatically decide, for each captured data item or observation task, whether to:
  1. `PROCESS_NOW`: Execute AI inference/filtering onboard immediately.
  2. `STORE_QUEUE`: Enqueue into a persistent buffer for time-shifted processing during high solar power or low thermal load.
  3. `TRANSMIT_RAW`: Queue raw high-resolution sensor frames directly for downlinking during ground station passes.
  4. `DISCARD_DROP`: Discard unusable frames (e.g., >30% cloud cover or night frames without IR relevance).
- **Core Reference Document:** [Docs/Problem_1_Process_or_Transmit_Master_Context.md](../../../Docs/Problem_1_Process_or_Transmit_Master_Context.md)
- **Detailed Mathematical Formulation:** [references/mathematical_formulation.md](./references/mathematical_formulation.md)
- **Telemetry & Workload Profiles:** [references/telemetry_and_workload_specs.md](./references/telemetry_and_workload_specs.md)
- **IEEE Paper & Video Pitch Rubric:** [references/ieee_paper_template_and_rubric.md](./references/ieee_paper_template_and_rubric.md)

---

## 2. Step-by-Step Development Workflow

### Step 1: Physical Environment & Orbital Simulator (`sim/`)
1. Implement an orbital clock stepping in discrete time increments ($\Delta t = 1\text{s}$ or $10\text{s}$).
2. Track physical state variables:
   - **Orbital position & illumination:** Sunlight ($P_{\text{harvest}}(t) > 0$) vs Eclipse ($P_{\text{harvest}}(t) = 0$).
   - **Ground station contact:** Binary indicator $G(t) \in \{0, 1\}$ (e.g. Tongchuan station pass: 270s contact every 3–4 orbits).
   - **Battery State of Charge:** 
     $$E_{\text{batt}}(t + \Delta t) = E_{\text{batt}}(t) + \min\left(P_{\text{harvest}}(t) - P_{\text{total}}(t), P_{\text{charge\_max}}\right) \Delta t$$
     Strict constraint: $E_{\text{batt}}(t) \ge 0.30 \cdot E_{\text{capacity}}$.
   - **Thermal state (Radiative balance in vacuum):**
     $$T_{\text{chip}}(t + \Delta t) = T_{\text{chip}}(t) + \frac{P_{\text{compute}}(t) - Q_{\text{rad}}(T_{\text{chip}}(t))}{C_{\text{thermal}}} \Delta t$$
     Constraint: $T_{\text{chip}}(t) \le 50.0^\circ\text{C}$.

### Step 2: Workload Ingestion & Profiling (`workloads/`)
For each incoming frame $k$, assign metadata:
- **Timestamp & Ground Coordinates:** $(t_k, \text{lat}_k, \text{lon}_k)$.
- **Raw Size:** $S_{\text{raw}} = 256 \times 256 \times 13 \times 1\text{ Byte} \approx 851.9\text{ KB}$ (Sentinel-2 13-band equivalent).
- **Cloud Coverage:** $R_{\text{cloud}} \in [0, 1]$. If $R_{\text{cloud}} > 0.30$, utility is penalized unless specific radar/IR task.
- **Scientific Utility Profile:** Base scientific value $U_0(k)$, deadline $\tau_k$, delay decay factor $\alpha_k$:
  $$U_k(t) = U_0(k) \cdot e^{-\alpha_k (t - t_k)} \quad \text{for } t \le t_k + \tau_k$$
- **Task Types & Model Properties:**
  - *Methane Leak Detection (EuroSat CNN):* $E_f \approx 0.041\text{ J}$, $T_f \approx 0.018\text{ s}$, compression ratio $C_f = 0.051$.
  - *Soil Moisture (BigEarthNet CNN):* $E_f \approx 0.092\text{ J}$, $T_f \approx 0.050\text{ s}$, $C_f = 0.041$.
  - *Urban Segmentation (U-Net):* $E_f \approx 0.755\text{ J}$, $T_f \approx 0.494\text{ s}$, $C_f = 0.047$.
  - *Vessel Detection (MASATI CNN):* $E_f \approx 1.053\text{ J}$, $T_f \approx 0.585\text{ s}$, $C_f = 0.026$.
  - *Wildfire Risk (Wildfire CNN):* $E_f \approx 0.667\text{ J}$, $T_f \approx 0.353\text{ s}$, $C_f = 0.026$.

### Step 3: Implement Benchmark Baselines (`policies/`)
To win the IEEE prize, you must experimentally prove superiority against standard industry baselines:
1. **Baseline 0 — Naive Transmit-All (Traditional EO):** Satellite performs zero on-orbit compute. Buffers all raw frames until ground station pass. (Demonstrates downlink bottleneck and heavy data drop due to storage overflow).
2. **Baseline 1 — Greedy Edge:** Every frame is processed immediately upon capture. If battery is low or chip overheats, invocations are dropped. (Demonstrates thermal throttling and power depletion).
3. **Baseline 2 — Multi-Threshold Rule Engine:**
   - If $R_{\text{cloud}} > 30\% \to$ Discard.
   - If $SoC > 75\%$ and $T_{\text{chip}} < 45^\circ\text{C} \to$ Process Onboard.
   - If ground station in sight and buffer non-empty $\to$ Downlink highest priority items.
   - Else $\to$ Enqueue into persistent storage.

### Step 4: Develop Proposed Intelligent Decision Engine
Choose one of two state-of-the-art formulations:
- **Approach A: Constrained Markov Decision Process (CMDP) / Reinforcement Learning (PPO)**
  - State $s_t$: $[SoC(t), T_{\text{chip}}(t), G(t), \text{Queue}_{\text{exec}}(t), \text{Queue}_{\text{downlink}}(t), \text{TaskPriority}, \text{CloudCover}, \text{SunlightFlag}]$.
  - Action $a_t \in \{\text{Process-Now}, \text{Queue-TimeShift}, \text{Transmit-Raw}, \text{Discard}\}$.
  - Reward $r(s_t, a_t) = U_k(t) - \lambda_{\text{energy}} E(a_t) - \lambda_{\text{drop}} \mathbb{I}(\text{dropped}) - \text{Penalty}(SoC < 30\% \text{ or } T > 50^\circ\text{C})$.
- **Approach B: Online Lyapunov Drift-Plus-Penalty Optimization (Recommended for Provable Real-Time Performance)**
  - Formulate virtual queues for battery debt $Q_{\text{batt}}(t) = \max(0, SoC_{\text{target}} - SoC(t))$ and thermal debt $Q_{\text{temp}}(t) = \max(0, T_{\text{chip}}(t) - T_{\text{target}})$.
  - Minimize the drift-plus-penalty function at each frame arrival without requiring heavy future prediction.

### Step 5: Automated Benchmarking & Visualization (`eval/`)
1. Generate standard comparative plots:
   - Cumulative Scientific Utility vs. Time (across 4 orbits / 6 hours).
   - Task Completion Rate (%) & Dropped Tasks.
   - Battery SoC trajectory over time showing avoidance of deep discharge (<30%).
   - Chip temperature curves proving adherence to $T_{\text{chip}} \le 50^\circ\text{C}$.
   - Downlink bandwidth utilization efficiency (insight vs. raw bytes).
2. Save summary metrics into structured JSON and markdown tables for direct insertion into the research paper.

### Step 6: Interim Research Paper Production (Phase 2 Deliverable)
Follow the IEEE double-column format detailed in [references/ieee_paper_template_and_rubric.md](./references/ieee_paper_template_and_rubric.md):
- **Section I: Introduction** (LEO data bottleneck, 3.07 GB/orbit vs. 600 kbps downlink, problem question).
- **Section II: Related Work** (Orbital edge computing, Trabant FaaS, Kodan, BUPT-1 telemetry).
- **Section III: System Model & Methodology** (Orbital energy/thermal equations, CMDP/Lyapunov formulation).
- **Section IV: Experimental Evaluation & Results** (Simulation setup, baseline comparison, metrics).
- **Section V: Roadmap & Conclusion** (Phase 3 hardware-in-the-loop plans, summary).

### Step 7: 2-Minute Pitch Video Storyboard
1. **0:00 – 0:30 (Hook & Problem):** The orbital bandwidth crisis: 95% of satellite data is discarded or delayed.
2. **0:30 – 1:00 (Core Innovation):** Autonomous Decision Engine combining FaaS time-shifting with energy/thermal awareness.
3. **1:00 – 1:40 (Simulation & Results):** Side-by-side comparison video/graph showing how our algorithm prevents overheating, respects battery limits, and delivers 3.5x higher scientific utility than traditional EO.
4. **1:40 – 2:00 (Impact & Roadmap):** Alignment with TUNSA and IASTAM 6.0 objectives; Phase 3 plans.
