# ASTRA: Adaptive Satellite Task and Resource Allocator for LEO Earth Observation

*IASTAM 6.0 Technical Challenge — Track 1: Artificial Intelligence and Onboard Computing (Problem 1)*

**Mohamed Habib Abid\*, Meriem Neffeti\***  
*Team IASTAM-OrbitEdge — [confirm official team and institution names]*  
*Tunisia*  
*Email: [confirm author email addresses]*  
*(\*Equal contribution)*

---

### Abstract
Small Earth-observation satellites capture multispectral and Synthetic Aperture Radar data under intermittent contact and constrained onboard resources. We introduce ASTRA (Adaptive Satellite Task and Resource Allocator), a research prototype for the IASTAM 6.0 "Process or Transmit?" problem. Its current experiments evaluate a seeded, one-second-step LEO simulator and an implemented threshold heuristic. Across five four-orbit episodes (seeds 42--46), the heuristic achieved a mean delivered-utility ratio of 0.0283 (sample standard deviation 0.0024; 95% t interval 0.0252--0.0313) and completed 1.53% of generated payloads. Mean modeled energy draw was 291.41 kJ, mean battery state of charge stayed above the 30% floor, and no safe-mode entry occurred. In a separate two-orbit trace (seed 42), simulated chip temperature reached 52.48$^\circ$C; the simulator throttles compute at 50$^\circ$C but does not enforce a hard temperature cap. Learned-policy, Lyapunov-scheduler, oracle, and hardware-calibration studies remain future work.

***Keywords—***orbital edge computing; onboard task scheduling; energy- and thermal-aware computing; Lyapunov optimization; reinforcement learning; Low Earth Orbit; fault tolerance.

---

## I. INTRODUCTION

The IASTAM 6.0 Technical Challenge, organized by IEEE IAS Tunisia with TUNSA, asks how an Earth-observation satellite should handle payloads under intermittent ground contact and onboard resource limits. Orbital edge computing concepts motivate processing selected data near the sensor [1], [8].

Within this domain, Problem 1 ("Process or Transmit?") targets an acute bottleneck in Earth Observation (EO): small satellites continuously capture high-resolution optical and Synthetic Aperture Radar (SAR) payloads (generating multi-megabyte payloads every $15\text{ s}$), yet operate under three binding physical constraints:
1. **Electrochemical Battery Degradation Floor:** The current simulator models a $100\text{ Wh}$ battery with a 30% minimum depth-of-discharge floor.
2. **Thermal Constraint:** The physical system requires radiative heat rejection in vacuum. The current simulator uses a first-order thermal proxy and pauses compute at 50$^\circ$C; it does not enforce a hard temperature limit, as the measured trajectory reaches 52.48$^\circ$C.
3. **Severe Downlink Bandwidth Choke:** Line-of-sight contact with ground stations is limited to short windows ($120\text{--}180\text{ s}$ per 90-minute orbit, about 2.8% mean contact duty cycle) with an X-band rate of $20.0\text{ Mbps}$ ($2.5\text{ MB/s}$).

For every captured payload, the onboard system must choose among four actions: `PROCESS_NOW` (compression vs. inference), `STORE_QUEUE` (time-shifted execution in Mass Memory Unit, MMU), `TRANSMIT_RAW` (downlink during line-of-sight passes), or `DISCARD_DROP` (pruning low-utility or cloud-occluded data). The optimization objective is to maximize cumulative scientific and operational utility, which decays exponentially over latency.

**Contributions:**
* **Simulator Characterization:** We evaluate the existing one-second LEO simulator, including solar profile, battery floor, simplified thermal dynamics, queueing, and stochastic SEU recovery.
* **Reproducible Evaluation:** We report a fixed-seed five-episode heuristic evaluation and expose current model limitations.
* **Empirical Multi-Orbit Benchmarking:** We characterize the implemented threshold heuristic across five four-orbit episodes, reporting eight outcome and resource metrics.
* **Roadmap:** Learned-policy, Lyapunov, and oracle comparisons are planned and not yet evaluated.

---

## II. RELATED WORK

### A. Orbital and Edge Computing Systems
Surveys of orbital edge computing delineate the compelling systems-level case for in-space processing: edge inference on commercial off-the-shelf (COTS) and radiation-tolerant hardware substantially mitigates downlink choke [1]. Serverless and cloud-native architectures for multi-tenant orbital platforms, such as Trabant [2] and studies on the Tiansuan constellation [3], demonstrate that containerized workloads can be time-shifted across orbital resource cycles. Broader treatments of Space AI [4] underscore the necessity of autonomous onboard classification, while Earth observation surveys [5] catalog compression and neural inference tradeoffs. Furthermore, space-grade FPGA neural accelerator benchmarks [6] and analytical studies on when to compute in space [7] establish the empirical energy-latency operating points adopted in our modeling.

### B. Control and Scheduling Paradigms
Resource-constrained orbital scheduling is addressed via two dominant paradigms:
1. **Lyapunov Optimization & Drift-Plus-Penalty:** Prior work [11] motivates an online scheduling approach; implementing and evaluating an orbital scheduler remains planned work.
2. **Constrained Reinforcement Learning (CMDP):** The repository has a Gymnasium environment; policy training and safety evaluation are not reported here.

### C. Added Value of This Work
Prior work motivates orbital edge processing and constrained scheduling. This interim study contributes a reproducible characterization of the current heuristic and identifies implementation gaps that must be resolved before comparative or safety claims can be made.

---

## III. METHODOLOGY

### A. Physical Models & Orbital Mechanics

The satellite orbital environment and hardware state at time $t$ are formalized in Table I.

**TABLE I: Primary System & State Variables**

| Symbol | Physical Definition | Nominal Value / Range |
| :--- | :--- | :--- |
| $\tau_{\text{orbit}}, \tau_{\text{sun}}$ | Orbit period / Sunlit duration | $5400\text{ s}$ (90 min) / $3300\text{ s}$ (55 min) |
| $P_{\text{harvest}}(t)$ | Solar power harvested | $0.0\text{ W}$ (eclipse) to $30.0\text{ W}$ peak ($22.5 \pm 7.5\text{ W}$) |
| $\text{SoC}(t)$ | Battery State-of-Charge | Floor: $\text{SoC} \ge 0.30$, Capacity: $100.0\text{ Wh}$ ($360\text{ kJ}$) |
| $T_{\text{chip}}(t)$ | Lumped simulated chip temperature | Ambient: $0^\circ\text{C}$; throttling threshold: $50^\circ\text{C}$ |
| $G(t)$ | Ground station line-of-sight flag | $\{0, 1\}$, randomized contact: $120\text{--}180\text{ s}$ per orbit (about 2.8\% mean duty) |
| $B_{\text{downlink}}$ | RF downlink communication speed | $20.0\text{ Mbps} = 2.5\text{ MB/s}$ ($15.0\text{ W}$ RF power) |
| $p_{\text{seu}}$ | Per-second simulated SEU event probability | $10^{-5}$ (Bernoulli RAM-reset event) |
| $M_{\text{mmu}}, M_{\text{ram}}$ | Mass Memory Unit / RAM capacity | $32\,000\text{ MB}$ ($32\text{ GB}$) / $4\,000\text{ MB}$ ($4\text{ GB}$) |

The SEU model draws a Bernoulli event each second with probability $10^{-5}$. An event wipes volatile RAM, resets accelerator state, and returns queued work to MMU for recovery; the simulator does not inject bit-level payload corruption.

#### 1) Power & Electrochemical Battery Dynamics
The simulator uses a 55-minute sunlit interval followed by a 35-minute eclipse. During sunlight, harvested power follows a sine-shaped profile between a 22.5 W base and a 30 W peak, with 30 s cosine tapers at sunlight boundaries; harvested power is zero in eclipse.

Net power balance integrates directly into battery energy $E_{\text{batt}}(t)$:
$$E_{\text{batt}}(t+1) = \min\left(E_{\text{cap}}, E_{\text{batt}}(t) + [P_{\text{harvest}}(t)-P_{\text{draw}}(t)]\Delta t\right)$$
where $P_{\text{draw}}(t)=P_{\text{base}}+P_{\text{compute}}(t)+P_{\text{comm}}(t)$, $P_{\text{base}}=5.0$ W, and radio power is 15.0 W when transmitting. The code applies no charge/discharge efficiency. Battery energy is clamped at the 30% depth-of-discharge floor on brownout; safe mode exits above 1.05 times the floor.

#### 2) Lumped Thermal Proxy
The current simulator uses a lumped first-order thermal proxy, not a Stefan--Boltzmann radiation model:
$$T_{\text{chip}}(t+1)=T_{\text{chip}}(t)+0.15P_{\text{draw}}(t)-0.10(T_{\text{chip}}(t)-T_{\text{amb}})$$
with one-second steps, $T_{\text{amb}}=0^\circ$C, and total bus, compute, and communication draw in watts. Compute is paused while temperature is at or above 50$^\circ$C. This threshold triggers throttling but is not a hard temperature cap: the seed-42 two-orbit trace reaches 52.48$^\circ$C.

### B. Workload, Queueing, and Utility Formulation

Payloads $k$ arrive periodically every $\Delta t_{\text{gen}} = 15\text{ s}$ across dual modalities:
* **Optical Multispectral ($70\%$):** Size $S_k \in [5, 15]\text{ MB}$, initial scientific utility $U_{0,k} \in [10, 100]$.
* **Synthetic Aperture Radar ($30\%$):** Size $S_k \in [100, 300]\text{ MB}$, initial scientific utility $U_{0,k} \in [10, 100]$.

Each payload's value decays exponentially over latency $(t - t_{\text{capture}})$:
$$U_k(t) = U_{0,k} \cdot \exp\left(-\alpha_k (t - t_{\text{capture}})\right)$$
with decay parameter $\alpha_k \in [10^{-4}, 10^{-3}]\text{ s}^{-1}$.

Compute actions transform payload properties:
* **Compression:** Duration $\Delta t_{\text{comp}} = 2\text{ s}$, power $P_{\text{comp}} = 10\text{ W}$, size reduction factor $C_{\text{ratio}} = 0.30$, utility retention $\rho_{\text{val}} = 0.90$.
* **Inference (Feature Extraction):** Duration $\Delta t_{\text{inf}} = 5\text{ s}$ (with $2\text{ s}$ wake-up penalty), power $P_{\text{inf}} = 20\text{ W}$ ($30\text{ W}$ wake), size reduction factor $C_{\text{ratio}} = 0.001$, utility retention $\rho_{\text{val}} = 0.50$.

---

### C. Decision Engine & Solution Schedulers

For each payload $k$ in mass memory, the agent selects an action $a_k \in \{\text{PROCESS\_COMPRESS}, \text{PROCESS\_INFER}, \text{DOWNLINK\_RAW}, \text{STORE\_QUEUE}, \text{DISCARD\_DROP}\}$:

```
                          ┌───────────────────────────┐
                          │   Incoming Sensor Frame   │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
                          ┌───────────────────────────┐
                          │  Mass Memory Buffer (MMU) │
                          └─────────────┬─────────────┘
                                        │
               ┌────────────────────────┴────────────────────────┐
               ▼                                                 ▼
      [In Ground Contact?]                             [Out of Ground Contact]
      ├── Yes: Downlink Raw or                          ├── High Power/Cool: Process Onboard
      │        Downlink Pre-Processed                   │   (Inference or Compression)
      └── No:  Hold in MMU Queue                        ├── Eclipse/Hot: Buffer in Queue
                                                        └── Storage Full: Discard Lowest Value
```

1. **Baseline Heuristic Policy:** A priority-ranked multi-threshold scheduler. During a ground station window ($G(t)=1$), it requests one highest-ranked payload per tick, respecting the shared 2.5 MB/s link budget. When battery SoC $> 0.50$, thermal headroom exists ($T_{\text{chip}} < 50^\circ\text{C}$), and queue depth $< 2$, it schedules compute tasks (selecting inference for payloads $< 50\text{ MB}$ and compression otherwise). Stale payloads ($U_k(t) < 5.0$) are evicted when MMU capacity exceeds $80\%$.
2. **Constrained MDP (Gymnasium Formulation):** State vector $s_t \in \mathbb{R}^{13 + 5K}$ captures normalized orbital phase, time-to-next-GS, SoC, temperature, queue depth, and top-$K$ payload metadata. Invalid action masks dynamically zero out impossible transitions (e.g., downlinking when $G(t)=0$, processing during safe mode, or double-queuing active tasks).
3. **Planned Lyapunov Scheduler:** Drift-plus-penalty scheduling is a Phase 3 target and is not implemented in the current repository.

---

## IV. EXPERIMENTS AND RESULTS

### A. Experimental Setup & Validation

The baseline evaluator ran the implemented heuristic for five four-orbit episodes (21,600 one-second steps each; seeds 42--46). This produces 1,440 generated payloads per episode. Values below are means, sample standard deviations, and 95% Student-t confidence intervals ($n=5$, 4 degrees of freedom). The decision-quality denominator is the simulator's snapshot sum of generated payload base values. Utilization is time-averaged occupancy; energy includes base, compute, and communication draw. Latency averages fully delivered payloads only. SEU confidence intervals are bounded below by zero; with five episodes, rare-event rates remain poorly estimated.

### B. Preliminary Results

Table II reports the metrics emitted by `python -m simulation.eval`; the episode summary is saved to `results/heuristic_summary.csv`. This is a single-policy characterization of the existing heuristic; no transmit-all, greedy-edge, RL, Lyapunov, or MILP comparison is claimed.

**TABLE II: Implemented Heuristic, Five Four-Orbit Episodes**

| Metric | Mean | Sample SD | 95% CI |
| :--- | ---: | ---: | :---: |
| Decision quality ($U_{\mathrm{downlink}}/U_{\mathrm{generated}}$) | 0.0283 | 0.0024 | [0.0252, 0.0313] |
| Completed-task rate | 0.0153 | 0.0010 | [0.0141, 0.0165] |
| Cumulative energy (kJ) | 291.414 | 1.850 | [289.117, 293.711] |
| Mean end-to-end latency (s) | 654.00 | 136.05 | [485.10, 822.89] |
| Time-averaged MMU utilization (%) | 37.497 | 2.094 | [34.897, 40.097] |
| Time-averaged RAM utilization (%) | 0.172 | 0.002 | [0.169, 0.175] |
| SEU events per episode | 0.400 | 0.548 | [0.000, 1.080] |
| Safe-mode events per episode | 0.000 | 0.000 | [0.000, 0.000] |

A separate seed-42 trajectory over two orbits is plotted in Fig. 1. SoC remained between 92.37% and 100%; chip temperature ranged from 0.75$^\circ$C to 52.48$^\circ$C. The 50$^\circ$C limit in this implementation is a throttling threshold, and the trace shows that it is not a guaranteed upper bound. This motivates replacing the simplified thermal proxy and validating safety behavior before making a hard-limit claim. The SEU model probabilistically wipes RAM and recovers queued work to MMU; five short episodes are insufficient to establish a fault-recovery rate.

![Battery state of charge and simulated chip temperature over two orbits; seed 42. Shading marks sunlight.](../results/figures/orbit_telemetry.svg)

*Fig. 1. Two-orbit heuristic telemetry (seed 42). The thermal trace exceeds the 50$^\circ$C throttling threshold.*

---

### C. Validation Plan for Phase 3

Building on these validated foundations, the Phase 3 implementation roadmap targets:
1. **Maskable PPO Reinforcement Learning:** Train a MaskablePPO agent in `simulation/rl_env.py` using `sb3-contrib` to optimize multi-step planning (e.g., pre-processing high-priority frames immediately prior to ground station rise).
2. **Lyapunov Scheduler:** Implement and evaluate drift-plus-penalty scheduling; no Lyapunov scheduler is present in the current codebase.
3. **MILP Oracle Ceiling:** Implement a mixed-integer linear program with non-causal orbital knowledge to quantify the utility upper bound.
4. **Stress Testing:** Validate robustness under anomalous conditions: solar flare SEU bursts ($p_{\text{seu}} = 10^{-3}$), battery cell degradation ($E_{\text{cap}} = 60\text{ Wh}$), and missed ground station contacts.

---

## V. CONCLUSION

We report a reproducible five-seed, four-orbit characterization of the implemented heuristic and its battery, queue, communication, and simplified thermal models. The observed heuristic decision-quality ratio is 0.0283 on the current simulator workload. The two-orbit trace also exposes a thermal-model limitation: simulated temperature can exceed the 50$^\circ$C throttling threshold. Next steps are comparative baselines, a validated thermal model with a hard safety guard, and implementation of Lyapunov and oracle schedulers before claims about their performance.

---

## REFERENCES

[1] B. Denby and B. Lucia, "Orbital Edge Computing: Machine Inference in Space," *IEEE Micro*, vol. 40, no. 1, pp. 7–15, Jan.–Feb. 2020.  
[2] T. Pfandzelter, N. Bauer, A. Leis, C. Perdrizet, F. Trautwein, T. Schirmer, O. Abboud, and D. Bermbach, "Trabant: A Serverless Architecture for Multi-Tenant Orbital Edge Computing," arXiv:2504.08337, 2025.
[3] C. Wang, Y. Zhang, Q. Li, A. Zhou, and S. Wang, "Satellite Computing: A Case Study of Cloud-Native Satellites," arXiv:2307.08530, 2023.
[4] Z. Wang, "Space AI: Leveraging Artificial Intelligence for Space to Improve Life on Earth," *arXiv preprint arXiv:2512.22399*, 2025.  
[5] A. Duggan, B. Andrade, and H. Afli, "Advancing Earth Observation: A Survey on AI-Powered Image Processing in Satellites," arXiv:2501.12030, 2025.
[6] P. Antunes and A. Podobas, "FPGA-Based Neural Network Accelerators for Space Applications: A Survey," arXiv:2504.16173, 2025 (version 3, June 2026).  
[7] R. Thummala and G. Falco, "When to Compute in Space," *arXiv preprint arXiv:2512.17054*, 2025.  
[8] B. Agüera y Arcas et al., "Towards a Future Space-Based, Highly Scalable AI Infrastructure System Design (Project Suncatcher)," *arXiv preprint arXiv:2511.19468*, 2025.  
[9] IEEE Industry Applications Society, "IASTAM 6.0 Technical Challenge Specification Book: Track 1 AI & Onboard Computing," IEEE IAS Tunisia Annual Meeting, 2026.  
[11] M. J. Neely, *Stochastic Network Optimization with Application to Communication and Queueing Systems*, Synthesis Lectures on Communication Networks, Morgan & Claypool Publishers, 2010.
