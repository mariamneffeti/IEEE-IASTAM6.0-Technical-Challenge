# IEEE IASTAM 6.0 — Track 1, Problem 1: "Process or Transmit?"
## Autonomous Agent & Pair Programming Guidelines

This file governs all agent behaviors, coding standards, mathematical modeling, and research methodologies within this repository.

---

### 1. Mission & Challenge Context
- **Competition:** IEEE IAS Tunisia Annual Meeting (IASTAM 6.0) Technical Challenge in collaboration with TUNSA (Tunisian Space Association).
- **Track 1:** Artificial Intelligence & Onboard Computing.
- **Problem Statement 1:** *"Process or Transmit?"*
  - **Core Problem:** An Earth Observation (EO) satellite continuously generates multispectral/hyperspectral imagery. Onboard resources—solar power harvesting, battery State-of-Charge (SoC), thermal dissipation via radiation, RAM/storage, and ground station line-of-sight communication windows—are strictly constrained.
  - **Objective:** Develop an autonomous decision engine / scheduling algorithm that dynamically decides for each incoming frame or task whether to:
    1. **`PROCESS_NOW`** onboard (run AI filtering/inference, produce high-value compressed insight $C_f \ll 1$ to drastically minimize downlink strain).
    2. **`STORE_QUEUE`** (time-shift execution into a persistent queue until solar power or thermal headroom permits, as in FaaS / Meta XFaaS / Trabant).
    3. **`TRANSMIT_RAW`** to ground (pass raw high-resolution bands directly when ground station is in sight and downlinking raw data is scientifically justified).
    4. **`DISCARD_DROP`** (drop invalid, cloudy, or low-utility frames during pre-filtering or quality thresholding).
  - **Optimization Target:** Maximize cumulative scientific & operational utility under dynamic orbital, thermal, energy, and communication constraints.

---

### 2. Physical & Orbital Invariants
All code, simulations, and algorithms in this repository **must** respect the laws of physics and orbital constraints:
1. **Orbital Dynamics:** Low Earth Orbit (LEO, 450–520 km altitude, sun-synchronous inclination ~97.3°, ~90-minute orbital period). The satellite experiences periodic sunlight (~45 min) and eclipse (~45 min).
2. **Ground Station Visibility:** Ground station contacts are short, intermittent windows (e.g., 5–10 minutes per orbit, ~0.75%–1.5% contact duty cycle). Antennas require dedicated RF power (e.g., 20W transmitter delivering 80–100 Mbps).
3. **Power Budget:** 
   $$P_{\text{generated}}(t) \ge P_{\text{compute}}(t) + P_{\text{comm}}(t) + P_{\text{base}}$$
   - Solar harvesting: 0W in eclipse, peaking up to 40W–48W in sunlight.
   - Base upkeep power: $P_{\text{base}} \approx 1.5\text{ W}$ (Raspberry Pi 4B class) to $12.6\text{ W}$ (full satellite bus).
   - Battery: Maximum Depth of Discharge (DoD) constraint (e.g., $SoC(t) \ge 30\%$ or $70\%$ capacity floor to prevent cell degradation).
4. **Thermal Dissipation in Vacuum:** No convection exists in space; cooling relies strictly on **radiative dissipation** ($Q = \epsilon \sigma A (T^4 - T_{\text{space}}^4)$). Compute chip temperature must stay strictly below safe operating limits ($T_{\text{chip}} \le 50^\circ\text{C}$).
5. **Radiation & SEU Fault Tolerance:** Single-Event Upsets (SEU) from cosmic radiation can trigger sudden hardware lockups or reboots. Computational state must be stateless (FaaS paradigm) or backed by atomic, persistent journal queues.

---

### 3. AI Engineering & Research Rigor Standards
1. **No Magic Numbers:** Every constant in scripts and models must have an explicit source citation (e.g., BUPT-1 telemetry trace, Sentinel-2 instrument spec, Trabant paper arXiv:2504.08337v1).
2. **Reproducibility First:**
   - Always fix random seeds (`numpy.random.seed(42)`, `torch.manual_seed(42)`).
   - Maintain clear separation between data traces, simulator engine, decision policies, and benchmark evaluators.
   - Experiments must run via CLI with explicit configuration files (`configs/*.yaml`).
3. **Mandatory Benchmarking Hierarchy:**
   Every proposed algorithm must be evaluated against standard reference baselines:
   - **Baseline 0 (Traditional EO):** Naive Transmit-All raw frames during ground station passes.
   - **Baseline 1 (Greedy Edge):** Always process onboard immediately; drop if overloaded.
   - **Baseline 2 (Static Rule-Based Heuristic):** Multi-threshold `if/else` on battery SoC and ground station visibility.
   - **Proposed Method (Dynamic Decision Engine):** E.g., Constrained MDP / Reinforcement Learning (PPO) or Online Lyapunov Drift-Plus-Penalty Optimization.
   - **Upper Bound (Offline Oracle):** Mixed-Integer Linear Program (MILP) with perfect non-causal orbital knowledge.
4. **Statistical Validity:** Run across multi-orbit traces (minimum 4 orbits / 6 hours, or full 24h orbit traces) across at least 3 repetitions; report mean, standard deviation, and 95% confidence intervals.

---

### 4. Key Deadlines & Deliverables (IASTAM 6.0)
- **Phase 2 Elimination Review:** **September 26, 2026** (Score $\ge 60/100$ to advance).
  - Deliverable 1: **Interim Research Paper** (IEEE double-column format).
  - Deliverable 2: **2-Minute Pitch Video** (Problem, Core Innovation, Simulation, Results).
- **Phase 3 Final Submission:** **October 14, 2026**.
  - Deliverables: Final technical report, documented GitHub repository, fully working prototype demonstrator.
- **D-Day Congress:** Final live pitch before expert jury + interactive Q&A + Scientific Poster presentation.

---

### 5. Scoring Grid Alignment (100 Points Total)
- **Understanding of the Problem (15 pts):** Rigorous satellite physics, orbital mechanics, bottleneck identification.
- **Relevance & Originality (15 pts):** Novelty of the decision policy beyond simple static heuristics.
- **Technical Architecture & Design (20 pts):** Clean, modular, serverless/time-shifted edge architecture.
- **Feasibility & Realism (15 pts):** Validated on real telemetry (BUPT-1, Sentinel-2, VIIRS) and COTS constraints.
- **Actual Prototype Progress (20 pts):** Fully functional simulator, working policies, benchmark curves.
- **Methodology & Planning (10 pts):** Adherence to roadmap, rigorous verification, clean git commits.
- **Presentation & Command (5 pts):** Clear, authoritative scientific writing and pitch defense.
