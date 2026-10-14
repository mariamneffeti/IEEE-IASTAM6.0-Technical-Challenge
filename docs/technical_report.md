# ASTRA: Adaptive Satellite Task and Resource Allocator

## Technical Report for IASTAM 6.0, Track 1, Problem 1

**Challenge:** “Process or Transmit?”

**Team:** Charmoula wMa9rou4

**Authors:** Mohamed Habib Abid; Mariam Neffeti

**Affiliations:** ISI El Manar and INSAT, Tunisia
**Report status:** Assessment report based on the repository snapshot dated 14 October 2026

---

## Executive Summary

Earth-observation satellites collect data faster than intermittent ground links can routinely return it. Their onboard scheduler must choose whether to process a payload, retain it for later, transmit it during contact, or discard it, while accounting for energy, storage, compute, temperature, data value, and latency. This report presents ASTRA (Adaptive Satellite Task and Resource Allocator), a reproducible software research prototype for the IASTAM 6.0 “Process or Transmit?” challenge. ASTRA contains a one-second, seeded low-Earth-orbit simulator; a conventional transmit-all policy; a greedy edge-processing policy; a threshold heuristic; and an exploratory MaskablePPO environment and checkpoint.

The checked-in paired benchmark evaluates four policies over five common-random-number scenarios, each spanning four 90-minute orbits. The threshold heuristic has the highest mean delivered-utility ratio (0.02860; sample standard deviation 0.00142; 95% Student-t interval [0.02683, 0.03036]). Greedy edge processing completes the greatest fraction of generated payloads (5.17%), while the heuristic completes 1.60% and has substantially shorter mean latency among completed deliveries (753 s versus 9,923 s). The single-seed PPO checkpoint delivers no payloads and is not evidence of an operational learned policy. These are synthetic simulator results, not flight measurements. The model uses a linear thermal proxy, and the recorded two-orbit trace reaches 52.48 °C despite a 50 °C compute-throttling threshold. A Lyapunov scheduler, mixed-integer offline oracle, real telemetry validation, and a hard thermal safety layer are not implemented. The report therefore presents ASTRA as an early prototype and a measured baseline study, and identifies the work required before making safety or generalization claims.

**Keywords—** orbital edge computing, Earth observation, satellite scheduling, energy-aware computing, downlink scheduling, reinforcement learning.

## 1. Challenge and Objectives

### 1.1 Problem statement

The challenge asks for an autonomous decision engine that maximizes the useful scientific and operational value delivered from Earth-observation data under constrained onboard resources and intermittent ground-station visibility. The required decision classes are:

| Decision | Intended meaning |
|---|---|
| `PROCESS_NOW` | Run onboard compression or inference to reduce transmitted data or extract an insight. |
| `STORE_QUEUE` | Retain a payload or task until resources or contact conditions improve. |
| `TRANSMIT_RAW` | Send the unprocessed payload during a ground contact when retaining its full data is warranted. |
| `DISCARD_DROP` | Remove low-utility or unusable data, subject to mission priorities. |

These choices are coupled. Processing consumes energy and can create heat, but can reduce downlink volume. Waiting preserves the option to process or transmit later but consumes finite mass memory and allows utility to decay. Transmitting requires line of sight and occupies a short, shared link window. Dropping saves resources but risks losing valuable observations.

### 1.2 Project objectives

ASTRA’s current research objectives are to:

1. Represent the coupled orbit, solar generation, battery, payload, storage, compute, thermal, and downlink dynamics in a deterministic, seedable simulator.
2. Provide clear reference policies and an initial learned-policy interface.
3. Compare policies using shared workload and environment seeds and report both outcomes and resource metrics.
4. Preserve a traceable distinction between implemented features, simulator assumptions, and planned flight-relevant capabilities.

The present work is a simulator and benchmark study. It does not demonstrate flight readiness, a formally safe controller, or a learned policy that outperforms the baselines.

## 2. System Overview

### 2.1 Current prototype architecture

The implementation separates the simulator from reference policies, the Gymnasium/MaskablePPO interface, and benchmark evaluation and plotting. The simulator owns the physical and workload state; policies read telemetry and request actions; the evaluator runs each policy against shared seeds and writes per-episode and summary CSV files. Orbital edge computing and serverless execution provide architectural context for processing near the sensor [1], [2]; the numeric workload and resource parameters here remain simulator assumptions.

```text
Synthetic payload arrivals ──► Mass-memory buffer ──► policy decision
                                      │                     │
                                      │             ┌───────┼────────┐
                                      │             ▼       ▼        ▼
                                      │          process  downlink   drop
                                      │             │       │
                                      └─────────────┴───────┘
                                                    │
                                     battery / thermal / storage
                                                    │
                                           telemetry and metrics
```

The separate architecture document describes a future cloud/ground and onboard FaaS design with model proposal, safety guard, fallback, state estimation, and operational logging. Those are design targets: the current code does not implement the proposed formally verified safety guard, cloud orchestration, model confidence routing, or an atomic persistent journal. The simulation’s queues and recovery logic are software abstractions, not flight-qualified persistence.

## 3. Simulator and System Model

### 3.1 Orbit, illumination, and ground contact

The simulation advances in one-second ticks on a 5,400 s (90-minute) orbit. Each orbit contains 3,300 s of modeled sunlight and 2,100 s of eclipse. During sunlight, generated power follows a sinusoidal profile with a 22.5 W base and 7.5 W amplitude, plus 30 s cosine tapers at the sunlight boundaries. Generated solar power is zero during eclipse. A randomized ground-station contact begins between 1,000 and 3,000 s into each orbit and lasts 120–180 s. Contacts are generated from the episode’s seeded random stream; this is not a geographic orbit propagator or a ground-station visibility calculation.

These choices approximate the challenge’s LEO setting but differ from some challenge-context examples, which use approximately equal sunlight/eclipses, longer 5–10 minute contacts, and higher peak solar/downlink rates. Therefore the benchmark describes the repository’s 55/35-minute orbit and 2–3-minute contact model, not every specification scenario. A configurable trace-driven orbital geometry model remains future work.

### 3.2 Power and battery

The default battery capacity is 100 Wh (360,000 J), the modeled minimum state-of-charge fraction is 0.30 (108,000 J), and base load is 5 W. Radio draw is 15 W when a downlink is active. Compression draws 10 W; inference draws 20 W while active and 30 W during accelerator wake. The battery update integrates the one-second net power balance and caps charging at capacity. If a tick falls below the floor, energy is clamped at the floor and safe mode is entered. Safe mode exits above 1.05 times the floor.

The implementation uses unit charge/discharge efficiency and starts episodes with a full battery. It does not implement battery aging, solar-array degradation, charge-rate limits, battery temperature, or a physically detailed cell model. The variable named `min_dod_fraction` is used as a minimum SoC fraction; it should be interpreted as a 30% SoC floor (70% maximum depth of discharge), not a 30% maximum DoD.

### 3.3 Thermal model

The simulator uses a one-node linear temperature proxy:

\[
T_{t+1}=T_t+0.15P_{t}-0.10(T_t-T_{amb}),
\]

where power includes base, compute, and communication draw, and the default ambient temperature is 0 °C. At or above 50 °C, processing is throttled. This is not the Stefan–Boltzmann radiation balance required for a physically grounded vacuum model, and the threshold is not a hard temperature bound: transient temperature can exceed it. In the documented seed-42, two-orbit trace, the peak is 52.48 °C. Consequently, this model cannot support a claim that ASTRA maintains the strict 50 °C safety invariant.

### 3.4 Payload generation, processing, and utility

The simulator creates one payload every 15 s. Payload modality is synthetic: optical with probability 0.70, or SAR with probability 0.30. Optical payload sizes range from 5 to 15 MB; SAR sizes range from 100 to 300 MB. Base values are drawn uniformly from 10 to 100, with optical value scaled by one minus a randomly drawn cloud fraction. Utility decays exponentially with age:

\[
U_k(t)=U_{0,k}\exp[-\alpha_k(t-t_k)],\qquad
\alpha_k\in[10^{-4},10^{-3}]\;\mathrm{s}^{-1}.
\]

Compression takes 2 s at 10 W and reduces the modeled payload to 30% of its size while retaining 90% of its value. Inference takes 5 s at 20 W after a 2 s, 30 W wake period; it reduces the payload to 0.1% of its size while retaining 50% of its value. A serial processing queue holds at most four jobs. These ratios, task values, cloud distribution, and resource rates are synthetic simulator parameters; the repository does not connect them to measured CNN benchmarks or validated Sentinel/BUPT telemetry.

### 3.5 Storage, RAM, and fault abstraction

The default mass-memory capacity is 32,000 MB and RAM is 4,000 MB. Payloads queued for processing remain accounted against mass memory until processing completes. RAM is used as a working copy for the active job. A per-second Bernoulli event with configured probability 10⁻⁵ resets RAM and accelerator state; queued work is recovered to mass memory by the simulator. This is an SEU proxy, not radiation transport, bit-error injection, or hardware reboot validation. No SEUs occurred in the five paired evaluation episodes, which provides little information about rare-event behavior.

### 3.6 Downlink

The modeled downlink rate is 20 Mbps, converted to 2.5 MB/s, with a 15 W radio draw. Transmission requires a ground-station pass and uses a shared per-tick bandwidth budget. The model does not include link margin, coding/FEC overhead, packet loss, protocol overhead, weather, pointing, antenna acquisition, or a geographic visibility trace.

## 4. Decision Policies and Learning Setup

### 4.1 Reference policies

| Policy | Implemented behavior | Purpose and interpretation |
|---|---|---|
| Transmit-all | Sends the oldest raw mass-memory payload during contact; no processing or voluntary drop | Conventional bent-pipe reference |
| Greedy-edge | Processes the oldest eligible payload whenever queue capacity permits; downlinks processed payloads during contact | Immediate-processing reference |
| Threshold heuristic | During contact, ranks payloads by processed status and current value for downlink; processes when SoC > 0.5, not throttling, and queue length < 2; drops low-value data when MMU exceeds 80% | Current ASTRA rule-based baseline |
| MaskablePPO | Uses telemetry and up to five payload slots, with invalid-action masks; checkpoint trained with seed 7 | Exploratory diagnostic only |

The baseline policies are operational comparison definitions, not optimized implementations. In particular, greedy edge is not configured to use a separate design-level safety supervisor, and the heuristic’s thresholds are chosen implementation rules rather than derived optimal thresholds.

### 4.2 PPO environment

The Gymnasium environment provides normalized system telemetry and metadata for a top-K set of payloads. Each of five payload slots can request no action, compression, inference, downlink, or drop. Invalid-action masks exclude actions judged unavailable in the current state. Reward is based on newly delivered utility, penalties for voluntary and involuntary drops, and safe-mode entry, with a small shaped reward for accepted processing actions to address delayed realization of utility at downlink.

The committed checkpoint metadata records training seed 7 and 100,352 actual training timesteps (100,000 requested). The benchmark evaluates this one checkpoint deterministically on disjoint environment seeds. A single training seed cannot characterize variability across training runs. Its zero-delivery result is a failure of this checkpoint under the reported evaluation, not evidence that reinforcement learning as a class is inferior.

### 4.3 Unimplemented benchmark targets

The challenge hierarchy calls for an online Lyapunov or other dynamic scheduler and an offline oracle, such as a MILP with future knowledge. Prior stochastic network optimization work provides background for an online scheduler [3], but neither method is implemented in this repository snapshot. ASTRA’s current learned policy is not a substitute for those missing comparisons. No performance claim relative to an oracle or Lyapunov policy is made here.

## 5. Evaluation Method

Four policies are evaluated on five common seeds (1001–1005), each for four orbits, or 21,600 one-second steps. The same seed gives each policy the same generated payloads, station windows, and SEU draws, enabling paired comparison. The results include per-policy means, sample standard deviations, and two-sided 95% Student-t intervals with four degrees of freedom. The paired-difference file reports episode-wise differences relative to the heuristic.

Reported metrics are:

* **Decision quality:** delivered utility divided by the sum of generated payload base values.
* **Completed-task rate:** fully downlinked payloads divided by generated payloads.
* **Energy:** cumulative modeled base, compute, and radio energy.
* **Latency:** mean capture-to-completion latency for fully delivered payloads.
* **MMU and RAM utilization:** time-average occupancy as a percentage of each capacity.
* **SEU and safe-mode events:** event count per episode.

The denominator for decision quality is a base-value snapshot and does not adjust for value retained after processing. Latency is conditional on completed deliveries; policies that deliver few payloads can have a misleadingly favorable or unfavorable mean. Metrics should therefore be read together. Five evaluation scenarios meet a minimum multi-orbit experiment but are too few for strong generalization or rare-event claims. PPO training-seed variability is not measured.

## 6. Results

### 6.1 Primary comparison

Table 1 reports the checked-in benchmark means, sample standard deviations, and 95% intervals.

**Table 1. Paired policy comparison, five four-orbit episodes (mean; sample SD; 95% Student-t interval).**

| Metric | Transmit-all | Greedy-edge | Heuristic | MaskablePPO, seed 7 |
|---|---:|---:|---:|---:|
| Decision quality | 0.00183; 0.00115; [0.00040, 0.00326] | 0.00470; 0.00105; [0.00339, 0.00601] | **0.02860; 0.00142; [0.02683, 0.03036]** | 0; 0; [0, 0] |
| Completed-task rate | 1.57%; 0.21%; [1.31%, 1.83%] | **5.17%; 0.80%; [4.17%, 6.17%]** | 1.60%; 0.05%; [1.54%, 1.66%] | 0; 0; [0, 0] |
| Energy | 117.15; 0.34; [116.73, 117.57] kJ | 290.88; 1.76; [288.70, 293.07] kJ | 290.88; 1.76; [288.70, 293.07] kJ | 206.01; 4.78; [200.07, 211.95] kJ |
| Completed-delivery latency | 9,659; 1,996; [7,181, 12,136] s | 9,923; 1,290; [8,322, 11,524] s | **753; 121; [603, 904] s** | N/A: no deliveries |
| Mean MMU utilization | 82.81%; 1.96%; [80.39%, 85.24%] | 38.16%; 1.91%; [35.79%, 40.54%] | 37.96%; 1.90%; [35.60%, 40.32%] | 48.77%; 3.63%; [44.27%, 53.28%] |
| Mean RAM utilization | 0; 0; [0, 0] | 0.173%; 0.003%; [0.169%, 0.177%] | 0.173%; 0.003%; [0.169%, 0.177%] | 0.439%; 0.036%; [0.394%, 0.484%] |
| SEU events per episode | 0 | 0 | 0 | 0 |
| Safe-mode events per episode | 0 | 0 | 0 | 0 |

### 6.2 Interpretation

The threshold heuristic delivered the largest fraction of generated base utility and had the shortest average latency among completed deliveries. Greedy edge processing completed the most payloads, but its delivered-utility ratio was lower than the heuristic’s. This illustrates why completion rate alone does not measure scientific value. Transmit-all used the least modeled energy but accumulated high memory occupancy and long delivery latency under the selected synthetic workload and contact schedule.

Greedy-edge and heuristic have identical per-seed aggregate energy in this experiment. The paired results show zero difference in energy for these seeds. This is a property of the observed run and model accounting, not a general equivalence between the policies. Their task selection and delivery outcomes differ.

The PPO checkpoint completed no tasks in any evaluation episode. Its lower energy than the two processing-heavy policies cannot be interpreted as an efficiency improvement because it produced no delivered utility; it also used more energy than transmit-all. This result is diagnostic and motivates further reward, training, and action-selection investigation.

No SEU or safe-mode events occurred in the paired benchmark. The separate heuristic telemetry trace has SoC between 92.37% and 100% and a temperature peak of 52.48 °C. Zero observed events over five episodes do not establish fault tolerance or safety. The thermal result directly shows that the current throttle is not a strict temperature cap.

The figures generated by the repository are [two-orbit telemetry](../results/figures/orbit_telemetry.pdf) and [policy comparison](../results/figures/policy_comparison.pdf). Episode-level observations and paired differences are available in [`results/comparison`](../results/comparison/).

## 7. Alignment with the Assessment Specification

| Assessment area | Evidence in ASTRA | Status and remaining evidence needed |
|---|---|---|
| Problem understanding and orbital constraints | Orbit/eclipse, solar input, battery, thermal proxy, storage, intermittent contact, utility decay | Prototype represents the constraint classes. Orbit and contact geometry are simplified, and some values differ from challenge examples. |
| Relevance and decision policy | Transmit-all, greedy-edge, heuristic, PPO | Multiple policies are compared. PPO currently delivers nothing; no Lyapunov method is implemented. |
| Architecture and design | Separate simulator, policy, evaluation, RL, and design modules | Software separation is present. FaaS orchestration, persistent atomic journal, and verified safety guard remain design targets. |
| Feasibility and realism | Explicit simulator parameters and synthetic payload modalities | No BUPT-1, Sentinel, VIIRS, or hardware-calibrated trace is used in the benchmark. Physical calibration is future work. |
| Prototype progress | Runnable simulation code, checkpoint, CSV benchmark outputs, figures | Functional software research prototype and reproducible artifacts are present; no flight or hardware-in-the-loop demonstration is documented. |
| Research methodology | Common random seeds; five four-orbit runs; means, SDs, 95% intervals; paired differences | A useful preliminary protocol is implemented. Broader seed counts, multiple PPO training seeds, stress scenarios, oracle and Lyapunov comparisons remain. |
| Communication and defense | Existing IEEE paper, pitch script, report and plotted outputs | This report gives a traceable account of evidence and limitations; confirm identities and submission metadata. |

## 8. Limitations and Validity

1. **Synthetic scenario:** Payload arrival, modality, sizes, values, cloud cover, station contacts, and processing ratios are generated from simulator parameters. There is no real observation or telemetry replay.
2. **Simplified orbital model:** The clock is periodic, with fixed sunlight/eclipse durations and randomized contact windows. It does not calculate orbital position, beta angle, station elevation, or contact geometry.
3. **Thermal safety gap:** The thermal equation is a linear proxy; the threshold pauses compute but does not clamp temperature. A trace exceeds the threshold. The current results cannot substantiate a strict 50 °C invariant.
4. **Simplified energy model:** The battery starts full, and charge/discharge efficiency and degradation are omitted. Some safe-mode decisions occur after actions in a tick have already been applied.
5. **SEU model:** The random reset abstraction does not model radiation dose, bit-level corruption, or hardware recovery. Five episodes with zero events do not evaluate rare-event robustness.
6. **Small evaluation sample:** Five evaluation seeds provide preliminary uncertainty estimates only. A single PPO training seed gives no estimate of training variability.
7. **Metric interpretation:** Delivered-utility ratio uses generated base-value snapshot; latency is computed only for completed deliveries. Those metrics can be affected by processing retention and selection effects.
8. **Missing reference methods:** No Lyapunov algorithm or non-causal MILP upper bound is available, so the study cannot establish performance against the full required benchmark hierarchy.
9. **Configuration and trace management:** Defaults live in `SimConfig`; `configs/` does not yet contain external YAML configuration loading. Reproducibility is supported through code defaults and metadata, but the specified configuration-file workflow is incomplete.
10. **Reference verification:** Citations inherited from the draft must be checked against the original papers and the challenge book before external submission. In particular, do not present simulator assumptions as empirical values from cited systems.

## 9. Conclusions and Completion Plan

ASTRA establishes a modular, seeded simulator and a first paired comparison of conventional transmission, immediate edge processing, a resource-aware heuristic, and an initial learned policy. In this experiment, the heuristic leads on delivered utility and completed-delivery latency; greedy edge processing leads on completion fraction; and the PPO checkpoint delivers no tasks. These findings are limited to a small synthetic benchmark and do not establish flight performance or safety. A measured temperature excursion above the throttle threshold, missing oracle and Lyapunov comparisons, and lack of real telemetry validation are material gaps against the challenge brief.

Recommended next steps, ordered by their effect on assessment credibility:

1. **Close the safety-model gap:** Replace or calibrate the thermal proxy with a radiative model and thermal capacitance/radiator assumptions; add an independent action safety guard; report both peak temperature and violations. Keep hard constraints distinct from throttling behavior.
2. **Align scenario assumptions:** Add a trace/configuration layer with cited sources for all constants and named challenge-aligned scenarios. Make sunlight, contact windows, radio rate/power, battery capacity, and base load explicit configurable inputs.
3. **Complete the benchmark hierarchy:** Implement a Lyapunov policy and a non-causal MILP oracle on the same workload, horizon, constraints, and objective. Label oracle performance as an upper bound under its stated assumptions.
4. **Improve statistical coverage:** Run at least three independent PPO training seeds and a larger held-out set spanning at least four orbits per episode; retain common-random-number pairing and report episode-level results, intervals, and paired differences.
5. **Validate inputs and hardware assumptions:** Incorporate documented public telemetry/workload traces where available, or clearly bound and sensitivity-test synthetic assumptions. Conduct hardware-in-the-loop measurement before making onboard execution claims.
6. **Complete reproducibility and fault evidence:** Move parameter sets into versioned YAML configs, record software versions and seeds, add contact-loss and SEU-burst stress scenarios, and demonstrate recovery of persistent state.
7. **Finalize submission metadata:** Confirm author names, affiliations, email addresses, contribution statement, figure attribution, bibliography, and requested assessment template. Rebuild the final PDF from the approved source and inspect its layout before delivery.

## References

1. B. Denby and B. Lucia, “Orbital Edge Computing: Machine Inference in Space,” *IEEE Computer Architecture Letters*, vol. 18, no. 1, pp. 59–62, 2019, doi: 10.1109/LCA.2019.2907539.
2. T. Pfandzelter et al., “Trabant: A Serverless Architecture for Multi-Tenant Orbital Edge Computing,” arXiv:2504.08337, 2025.
3. M. J. Neely, *Stochastic Network Optimization with Application to Communication and Queueing Systems*. Morgan & Claypool, 2010.

---

**Submission note:** The values above should be regenerated if the simulator, checkpoint, or result CSVs change. The team should confirm the final submission format and check every claim against the underlying materials before presenting it.
