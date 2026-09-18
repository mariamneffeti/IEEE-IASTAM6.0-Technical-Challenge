# Problem 1: "Process or Transmit?" — Master Research & Engineering Context

**IEEE IAS Tunisia Annual Meeting (IASTAM 6.0) Technical Challenge**  
*Organized in collaboration with the Tunisian Space Association (TUNSA)*  
**Track 1:** Artificial Intelligence & Onboard Computing  
**Problem 1:** Process or Transmit?

---

## 1. Executive Summary & Challenge Mandate

### 1.1 The Challenge Setting
As Earth Observation (EO) sensors transition from standard optical framing to high-resolution multispectral, hyperspectral, and Synthetic Aperture Radar (SAR) payloads, the volume of raw data generated in Low Earth Orbit (LEO) has outpaced the communication capacity of downlink links. A standard LEO nanosatellite capturing $256 \times 256$ frames at 10 m/pixel across 13 spectral bands generates over **3.07 GB of raw data per 90-minute orbit**, while ground station communication windows are intermittent (~5–10 minutes per pass), offering an effective continuous downlink throughput of only **~600 kbps**.

### 1.2 The Core Research Question
> *"How can the system decide automatically, for each piece of data or task, whether it is preferable to process it immediately onboard, store it for later processing, or transmit it to the ground?"*

### 1.3 The Objective
Develop an autonomous, resource-aware decision engine and task scheduling framework that maximizes the cumulative scientific and operational utility of captured Earth observation data while strictly adhering to the dynamic physical constraints of a LEO nanosatellite (energy harvesting, battery degradation limits, vacuum radiative thermal dissipation, onboard storage capacity, and intermittent ground station contact).

---

## 2. Low Earth Orbit (LEO) Spacecraft Physics & Environmental Constraints

To build a scientifically rigorous and defensible solution, the decision engine must model the coupled thermodynamics, power systems, and orbital mechanics of spaceflight.

```
                    ┌──────────────────────────────────────────────┐
                    │               ORBITAL DYNAMICS               │
                    │   LEO 500km | 90-min Period | Sun-Sync 97°   │
                    └──────────────────────┬───────────────────────┘
                                           │
                    ┌──────────────────────┴───────────────────────┐
                    ▼                                              ▼
    ┌───────────────────────────────┐              ┌───────────────────────────────┐
    │     SUNLIT PASS (~45 min)     │              │      ECLIPSE (~45 min)        │
    │  • Solar Harvest: 10W - 48.6W │              │  • Solar Harvest: 0.0 W       │
    │  • Battery Charging           │              │  • Battery Discharging        │
    │  • High Sensor Activity       │              │  • Storage & Low-Power Tasks  │
    └───────────────┬───────────────┘              └───────────────┬───────────────┘
                    │                                              │
                    └──────────────────────┬───────────────────────┘
                                           │
                    ┌──────────────────────┴───────────────────────┐
                    │              PHYSICAL BOUNDARIES             │
                    │  • Thermal: Radiative Cooling (T_chip ≤ 50°C)│
                    │  • Battery: Discharge Floor (SoC ≥ 30%)      │
                    │  • Comms: Line-of-Sight Windows (~0.75%)     │
                    └──────────────────────────────────────────────┘
```

### 2.1 Orbital Dynamics & Energy Harvesting
- **Orbit Profile:** Sun-synchronous orbit (SSO), altitude $h \approx 487\text{ km} - 520\text{ km}$, inclination $i \approx 97.3^\circ$.
- **Orbital Period:** $\tau_{\text{orbit}} \approx 94\text{ minutes}$ (~15.3 orbits per day).
- **Illumination Cycle:** The satellite alternates between direct solar illumination (~45–50 min) and Earth eclipse (~40–45 min).
- **Solar Harvesting ($P_{\text{harvest}}(t)$):**
  - In darkness: $P_{\text{harvest}}(t) = 0.00\text{ W}$.
  - In sunlight: $P_{\text{harvest}}(t)$ varies between $10\text{ W}$ and $48.59\text{ W}$ depending on solar vector angle $\theta(t)$ and panel articulation.
  - **Empirical Baseline (BUPT-1 satellite trace):** Mean generated solar power is $15.59\text{ W}$; base satellite housekeeping draws $12.64\text{ W}$, leaving a **mean net available compute/communication power of $2.950\text{ W}$ ($2950\text{ mW}$)**.

### 2.2 Battery Health & Energy Storage Dynamics
- **Capacity:** $57.5\text{ Wh} = 207,000\text{ J}$ (dedicated compute partition of a $115\text{ Wh}$ bus).
- **Depth-of-Discharge (DoD) Protection:** Lithium-ion cells degrade rapidly if discharged deeply. The State of Charge (SoC) must never drop below $30\%$ ($SoC(t) \ge 0.30$, or $E_{\text{batt}}(t) \ge 62,100\text{ J}$).
- **Energy Balance Equation:**
  $$\frac{dE_{\text{batt}}}{dt} = \eta_{\text{charge}} [P_{\text{harvest}}(t) - P_{\text{total}}(t)]^+ - \frac{1}{\eta_{\text{discharge}}} [P_{\text{total}}(t) - P_{\text{harvest}}(t)]^+$$
  where $P_{\text{total}}(t) = P_{\text{base}} + P_{\text{compute}}(t) + P_{\text{comm}}(t)$.

### 2.3 Vacuum Radiative Thermodynamics
- **The Vacuum Bottleneck:** In space vacuum, heat transfer by air convection is exactly zero ($h_{\text{conv}} = 0$). All heat generated by processors must be dissipated via **conduction through the satellite chassis and radiative emission** into deep space ($T_{\text{space}} \approx 3\text{ K}$):
  $$Q_{\text{rad}} = \epsilon \sigma A_{\text{rad}} (T_{\text{chassis}}^4 - T_{\text{space}}^4)$$
- Small CubeSats have limited surface area ($A_{\text{rad}}$). Continuous compute execution at 100% CPU/GPU quickly induces thermal runaway.
- **Operating Temperature Boundary:** Commercial-off-the-shelf (COTS) processors (e.g. Raspberry Pi 4B, NVIDIA Jetson Nano) must maintain junction temperature **$T_{\text{chip}}(t) \le 50.0^\circ\text{C}$** to avoid permanent hardware damage or thermal throttling.

### 2.4 Communication Architecture & Ground Station Passes
- **Ground Contact Geometry:** Satellites in LEO only communicate when passing within line-of-sight of authorized ground stations.
- **Contact Ratio:** Typical mid-latitude stations (e.g. Tongchuan, China or Tunis, Tunisia) have contact windows lasting only **$270\text{ seconds}$** (~4.5 minutes) every 3 to 4 orbits, yielding an operational contact duty cycle of **only $0.75\%$**.
- **Downlink Physical Layer:** $100\text{ Mbps}$ raw ($80\text{ Mbps}$ net after 20% protocol/FEC overhead). Active transmission draws **$20.0\text{ W}$** of RF power.
- **Downlink Energy Metric:**
  $$E_{\text{sendbyte}} = \frac{20\text{ W}}{80 \times 10^6\text{ bits/s}} \times 8\text{ bits/Byte} = 2.0 \times 10^{-6}\text{ J/Byte} = 2.0\ \mu\text{J/Byte}$$
- **Uplink Channel:** Narrowband ($1\text{ Mbps}$ raw, $800\text{ kbps}$ net), reserved for Telemetry, Tracking & Command (TT&C) and lightweight code deployments.

---

## 3. The Core Dilemma: "Process or Transmit?"

The system must decide for every piece of collected data whether to process onboard, time-shift into a queue, transmit raw, or discard.

| Decision Action | Bandwidth Required | Energy Consumed | Latency / Time-to-Insight | Best Suited Scenario | Risk / Failure Mode |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`PROCESS_NOW`** | **Minimal** (1%–5% of raw size via compression ratio $C_f$) | High compute power ($E_f \approx 0.04\text{J} - 1.05\text{J}$) | **Lowest** (immediate inference) | High-priority events (wildfire, flood), ample solar energy, low chip temp. | Overheating ($T_{\text{chip}} > 50^\circ\text{C}$), battery depletion during eclipse. |
| **`STORE_QUEUE`** | None currently | Zero active compute (idle baseline only) | Deferred (delayed until sunlit/cooled) | Sub-optimal power or thermal state, medium-priority tasks with flexible deadlines. | Storage overflow, insight latency decay, task deadline expiration. |
| **`TRANSMIT_RAW`** | **Massive** (100% of raw frame, ~852 KB) | High RF transmitter power ($20\text{ W}$, $2\mu\text{J/B}$) | Intermittent (waits for ground station pass) | Ground station in sight, complex tasks exceeding onboard compute capability. | Bandwidth saturation, dropped raw frames due to buffer overflow. |
| **`DISCARD_DROP`** | Zero | Pre-filter cost only ($0.01\text{ J}, 0.038\text{ s}$) | N/A | Cloud cover $>30\%$, dark optical frames, out-of-bounds regions of interest. | False negatives (dropping critical target data due to misclassification). |

---

## 4. Architectural Blueprint: Serverless Orbital Edge Engine

Drawing from the proven **Trabant architecture** (Pfandzelter et al., arXiv:2504.08337v1), our framework adopts the **Function-as-a-Service (FaaS)** paradigm to achieve robust multi-tenant execution and time-shifted computing.

```
  ┌─────────────────┐
  │  Optical Sensor │ (Sentinel-2 13-band multispectral frames @ 2.5 Hz)
  └────────┬────────┘
           │ Raw Frames (852 KB each)
           ▼
  ┌─────────────────────────────────────────────────┐
  │  PREPROCESSING & PRE-FILTERING                  │
  │  • Pixel-level cloud detection (Braaten-Cohen)  │
  │  • Cloud Cover > 30% or Darkness -> DISCARD     │
  └────────┬────────────────────────────────────────┘
           │ Filtered Frames (Pass Rate ~ 23%)
           ▼
  ┌─────────────────────────────────────────────────┐
  │      AUTONOMOUS DECISION ENGINE (BRAIN)         │
  │  Inputs: SoC(t), T_chip(t), G(t), Queues, Value │
  │  Policies: Lyapunov / CMDP / Priority Rules     │
  └────────┬───────────────┬────────────────────────┘
           │               │
     Process / Queue       │ Transmit Raw
           │               │
           ▼               ▼
  ┌─────────────────┐   ┌──────────────────────┐
  │ EXECUTION QUEUE │   │ DOWNLINK BUFFER      │
  │  (Persistent)   │   │  (Ready for Station) │
  └────────┬────────┘   └──────────┬───────────┘
           │                       │
           ▼                       ▼
  ┌─────────────────┐   ┌──────────────────────┐
  │ FaaS EXECUTOR   │   │ RF TRANSMITTER       │
  │  • func_methane │   │  • 100 Mbps Link     │
  │  • func_wildfire│   │  • Active during     │
  │  • func_vessel  │   │    ground pass       │
  └────────┬────────┘   └──────────┬───────────┘
           │ (Compressed Insight)  │
           └───────────────────────┘
```

### 4.1 Trabant Mathematical Invariants
Any valid schedule must satisfy the fundamental system constraints:
1. **Power Feasibility:**
   $$P_{\text{harvest}}(t) \ge P_{\text{compute}}(t) + P_{\text{comm}}(t)$$
2. **Compute Power Budget:**
   $$P_{\text{compute}} = P_{\text{base}} + E_{\text{pre}} R_{\text{frame}} + \sum_{i=1}^n E_{f_i} R_{\text{frame}} (1 - R_{\text{filter}})$$
3. **Communication Power Budget:**
   $$P_{\text{comm}} = E_{\text{sendbyte}} \sum_{i=1}^n C_{f_i} R_{\text{frame}} (1 - R_{\text{filter}}) S_{\text{frame}}$$
4. **Downlink Bandwidth Budget:**
   $$B_{\text{downlink}} \ge \sum_{i=1}^n C_{f_i} R_{\text{frame}} (1 - R_{\text{filter}}) S_{\text{frame}}$$
5. **Real-time Processing Throughput:**
   $$R_{\text{frame}}^{-1} \ge T_{\text{pre}} + \sum_{i=1}^n T_{f_i} (1 - R_{\text{filter}})$$

---

## 5. Machine Learning Workload Suite

The framework benchmarks five representative Earth Observation micro-services running on lightweight runtimes (TensorFlow Lite / ONNX):

```
1. Methane Leak Detection (EuroSat CNN)
   ├── Bands: RGB (B2, B3, B4) + SWIR (B11, B12)
   ├── Computation: 0.018s | Energy: 0.041J
   └── Compression: 5.1% (Outputs cropped bounding box + SWIR channels)

2. Soil Moisture Multi-label (BigEarthNet CNN)
   ├── Bands: 12 Bands
   ├── Computation: 0.050s | Energy: 0.092J
   └── Compression: 4.1% (Outputs classification vector + moisture indices)

3. Urban Semantic Segmentation (U-Net)
   ├── Bands: RGB
   ├── Computation: 0.494s | Energy: 0.755J
   └── Compression: 4.7% (Outputs binary infrastructure mask)

4. Marine Vessel Detection (MASATI CNN)
   ├── Bands: RGB (strict cloud threshold < 10%)
   ├── Computation: 0.585s | Energy: 1.053J
   └── Compression: 2.6% (Outputs coordinates of detected ships)

5. Wildfire Risk Detection (Wildfire CNN)
   ├── Bands: All 13 Bands
   ├── Computation: 0.353s | Energy: 0.667J
   └── Compression: 2.6% (Preserves multispectral data only if fire prob > 60%)
```

---

## 6. Decision Algorithms & Benchmarking Strategy

To ensure a top-tier scientific defense before the jury, we formulate a progressive benchmarking hierarchy:

### 6.1 Baseline 0: Traditional Earth Observation (Transmit-All)
- Satellite acts strictly as a sensor collector. All captured frames are buffered into storage and dumped verbatim during ground station contacts.
- **Flaw:** Buffer overflow drops $>70\%$ of frames; latency is several orbits long.

### 6.2 Baseline 1: Greedy Edge Processing
- Every frame passing pre-filtering is processed immediately onboard.
- **Flaw:** Battery is depleted below $30\%$ during eclipse; chip temperature exceeds $50^\circ\text{C}$, triggering hardware throttling.

### 6.3 Baseline 2: Multi-Threshold Rule Engine
- Static rules:
  - If $SoC > 75\%$ AND $T_{\text{chip}} < 45^\circ\text{C} \to$ `PROCESS_NOW`
  - Else if Ground Station Visible $\to$ `TRANSMIT_RAW`
  - Else $\to$ `STORE_QUEUE`
- **Flaw:** Cannot adapt dynamically to variable sunlight, differing task values, or varying deadlines.

### 6.4 Proposed Solution: Online Lyapunov Drift-Plus-Penalty Optimization
- Models battery deficit and thermal excess as virtual queues:
  $$Q_{\text{batt}}(t) = \max(0, SoC_{\text{safe}} - SoC(t)), \quad Q_{\text{temp}}(t) = \max(0, T_{\text{chip}}(t) - T_{\text{safe}})$$
- Minimizes the Lyapunov drift-plus-penalty trade-off in real time:
  $$\min_{a_t \in \mathcal{A}} \left[ \Delta V(t) - V \cdot \text{Utility}(a_t) \right]$$
- **Advantages:** Provable queue stability, zero thermal violations, no complex neural training required onboard, $O(1)$ real-time execution.

### 6.5 Theoretical Upper Bound: Global Offline Oracle (MILP)
- Solves the global mixed-integer program with perfect future knowledge over all $T$ time steps to establish the theoretical maximum achievable utility.

---

## 7. Challenge Roadmap & Deliverables Alignment

### Phase 2: Research & Initial Development (Deadline: September 26, 2026)
- [x] Complete challenge and domain context formulation.
- [x] Create workspace skills and engineering rules.
- [ ] Build discrete-event orbital simulation harness in Python (`sim/`).
- [ ] Implement baseline and Lyapunov decision policies.
- [ ] Generate comparative benchmark curves (utility, energy, thermal, latency).
- [ ] Draft **Interim Research Paper** in IEEE double-column format.
- [ ] Record **2-Minute Pitch Video** following official storyboard.

### Mid-Review Elimination Round (September 26–30, 2026)
- **Elimination Threshold:** Must score **$\ge 60/100$** to qualify for Phase 3.

### Phase 3: Final Development (October 1–14, 2026)
- Incorporate jury feedback from mid-review.
- Hardware-in-the-loop validation (emulating Raspberry Pi 4B telemetry).
- Edge fault injection (Single-Event Upset lockup recovery test).
- Complete final technical report, GitHub documentation, and demonstrator GUI.

### Phase 4: Congress & Poster Session (D-Day)
- Live pitch defense before TUNSA & IEEE jury.
- Presentation of official scientific poster.
