# Satellite Simulation: Design Choices and Physics

This document explains what `satellite_sim.py` models, why each choice was made, and where the model is a simplification. All numbers below were computed from the default `SimConfig`. Figures marked *(estimate)* are back-of-envelope values, not measured simulator output.

---

## 1. Purpose and mapping to IASTAM Problem 1

The simulator is a testbed for **Track 1, Problem 1: "Process or Transmit?"**. A satellite produces data continuously, but compute, energy, storage and downlink time are limited. For each payload, a controller must choose to process it onboard, store it, or transmit it.

| Problem 1 element | Where it lives in the code |
|---|---|
| Process onboard | `process` action: compression or inference |
| Store for later | `mmu_payloads` (mass memory), with capacity and decay of value over time |
| Transmit | `downlink` action, only during a ground-station (GS) pass |
| Energy | `PowerSubsystem`, solar model, per-task power draws |
| CPU/GPU load, thermal | `ThermalSubsystem`, throttling, accelerator wake state |
| Memory / storage | `StorageMemorySubsystem` (MMU + RAM) |
| Data priority | `Payload.base_value` and exponential time decay |
| Communication windows, bandwidth | `Environment` GS pass, `downlink_bandwidth_mbps` |
| Transmission delay | Latency counters; decay makes waiting costly |

The evaluation criteria in the specification (decision quality, completed-task rate, energy, latency, resource utilisation) are computed from raw counters kept on `Satellite`, independent of any RL reward (Section 10).

**Scale note.** The parameters describe a *small Earth-observation satellite* (tens of watts, roughly 100 Wh battery), not a data-center-class orbital platform. The relative trade-offs (process vs. transmit, compress vs. infer) are what the study depends on, not the absolute wattage.

**Architecture.** `satellite_architecture.svg` shows the modules, the agent interface (actions in, telemetry and feedback out) and the couplings between subsystems (power draw, thermal throttling, safe mode, SEU recovery).

---

## 2. Time, ticks and determinism

- **One tick = 1 second.** Every period is in seconds, and power in watts integrates directly to joules: `1 W x 1 s = 1 J`.
- **Tick order** inside `Satellite.step()`:
  1. Environment advances (orbit phase, solar power, GS window)
  2. New payload generated (every 15 s)
  3. SEU check
  4. Safe-mode check (with hysteresis)
  5. Agent actions executed (process / downlink / drop)
  6. Processing queue advances one step
  7. Physics: battery, thermal, counters
- Actions act on the state *after the previous tick*. A payload that arrives this tick cannot be referenced by an action this tick, because the agent has not seen its ID yet.
- **One shared `random.Random(seed)`** feeds the GS schedule, the SEU roll and payload generation. No random draw depends on the agent's actions: the SEU roll happens every tick, payloads are generated on a fixed clock, and GS windows are rolled at orbit boundaries. So the same seed produces the **identical payload stream, GS schedule and SEU events for every policy**.
- This is the *common random numbers* technique. It makes heuristic-vs-RL comparisons **paired**: differences between policies come from their decisions, not from luck in the environment. `sanity_check.py` verifies it (Check 4).

---

## 3. Orbit and Sun

| Parameter | Value | Meaning |
|---|---|---|
| `orbit_period_s` | 5400 s (90 min) | Typical low-Earth-orbit period |
| `sunlit_duration_s` | 3300 s (55 min) | 61% sunlit |
| Eclipse | 2100 s (35 min) | 39% in Earth's shadow |

The sunlit fraction is fixed. In reality it varies through the year with the orbit's beta angle, and some orbits are sunlit almost continuously. Fixing it keeps every episode comparable. It can be varied later as a stress scenario.

---

## 4. Power subsystem

### 4.1 Solar generation

```
P_solar(t) = (22.5 + 7.5 * sin(pi * t / T_sun)) * blend(t)     for 0 <= t < T_sun
P_solar(t) = 0                                                 during eclipse
```

- **Half-sine shape (22.5 to 30 W).** A flat panel's output scales with the cosine of the sun incidence angle. As the satellite crosses the sunlit arc, the effective angle changes, so power rises to a mid-arc peak and falls again. The half-sine is a simple proxy, not a full attitude model.
- **Cosine taper (`solar_transition_s = 30`).** Entering or leaving eclipse is not instantaneous: the Sun is a disc, so the spacecraft passes through a penumbra. `blend = 0.5 * (1 - cos(pi * t / 30))` ramps from 0 to 1 smoothly. This also avoids a step discontinuity that would look artificial in plots and could confuse a learning agent. The guard in `__post_init__` rejects a taper longer than half the sunlit window, because the two ramps would overlap.

**Energy per orbit** (computed): about **89.3 kJ (24.8 Wh)** generated. The 5 W base load uses **27 kJ (7.5 Wh)**. That leaves a **discretionary surplus of about 62 kJ (17.3 Wh) per orbit** for compute and communication. This budget is what makes energy a real constraint.

### 4.2 Battery

The battery is an energy bucket:

```
E_batt(t+1) = min(E_capacity, E_batt(t) + P_solar - P_draw)
```

| Quantity | Value |
|---|---|
| Capacity | 100 Wh = 360,000 J |
| Floor (`min_dod_fraction = 0.3`) | 108,000 J (30% state of charge) |
| Usable energy above the floor | 252,000 J (70 Wh) |
| Safe-mode exit threshold | 113,400 J (31.5% state of charge) |

**Naming note.** The config field is called `min_dod_fraction`, but 0.3 is the minimum *state of charge*, so the maximum depth of discharge is 70%. LEO satellites cycle their batteries about 15 times a day, so designs keep depth of discharge well below 100% to protect battery life. That is the reason for the floor. Consider renaming the field to `min_soc_fraction` in the paper's parameter table.

### 4.3 Safe mode and hysteresis

If the battery reaches the floor (or a tick would push it below), the satellite enters **safe mode**:
- All agent actions are discarded.
- Every queued job is cancelled: its payload returns to the `mmu_payloads` list (MMU accounting is unchanged) and the accelerator is reset.
- Only the base load remains.

Safe mode exits only when the battery rises above **1.05 x floor** (`safe_mode_exit_margin`). This hysteresis band (5,400 J, about 250 s of sunlit surplus) prevents rapid enter/exit chattering at the boundary, which is how real flight software behaves. The RL reward penalises entering safe mode heavily (-500), because losing a mission's autonomy is far worse than losing one payload.

---

## 5. Compute: compression vs. inference

Two processing modes turn a raw payload into something cheaper to send:

| | Compression (CPU) | Inference (accelerator) |
|---|---|---|
| Duration | 2 s | 5 s (+2 s wake if cold) |
| Power | 10 W | 20 W active, 30 W during wake |
| Marginal energy per job | **20 J** | **100 J** (warm) or **160 J** (cold) |
| Output size | 30% of input (`compression_ratio`) | 0.1% of input (`inference_ratio`) |
| Value kept | 90% (`compression_value_ratio`) | 50% (`inference_value_ratio`) |

**Interpretation.** Compression is like lossy image compression: the image survives, at a modest quality cost. Inference extracts *information* (for example detections or labels) instead of pixels. It shrinks the data a thousand-fold but cannot be reconstructed, hence the larger value loss. This mirrors Problem 7 in the spec: transmit information, not raw data.

**The value and size ratios are design parameters, not measurements.** They were chosen to create a real trade-off. Without the value loss, inference would strictly dominate compression on every metric except energy. This is exactly what the Phase 7 ablation ("remove inference value degradation") tests.

### 5.1 Accelerator wake-up state machine

`sleep -> waking (2 ticks at 30 W, no progress) -> active (20 W, progress)`.

- A cold start costs an extra 60 J and 2 s of latency.
- The accelerator parks back to `sleep` on a tick where step 5 finds the queue empty or the chip throttled while the state is `active`. Compression jobs leave the state untouched (Section 12, item 10).
- **Consequence: batching pays.** Running several inference jobs back-to-back keeps the accelerator warm and saves 60 J per job (37%). A policy that infers one payload every 15 s pays the cold cost every time.

### 5.2 Serial compute and the bounded queue

The queue runs **one job at a time** and holds at most **`max_queue_length` = 4** jobs (the active one plus up to three waiting). There is no parallelism, and compute time is small next to the time payloads wait for a pass. Inference at 5 s per job uses about 33% of the 15 s arrival interval, so compute *throughput* is not the constraint. The constraints are energy, thermal behaviour and downlink volume.

**Energy check (computed).** Inferring every payload costs 360 x 100 J = 36 kJ per orbit (batched) to 360 x 160 J = 57.6 kJ (all cold). Against the ~62 kJ surplus, this is close to the budget but not over it. Compressing everything costs only about 7 kJ.

---

## 6. Thermal subsystem

A lumped-capacitance (one-node) model:

```
T(t+1) = T(t) + 0.15 * P_total - 0.10 * (T(t) - T_ambient)
```

Reading the coefficients as `1/C` and `G/C`: thermal capacitance **C ~ 6.7 J/K**, conductance to the environment **G ~ 0.67 W/K**, time constant **tau = C/G ~ 10 s** (9.5 s in discrete form). The steady state is `T = T_ambient + 1.5 * P_total`.

| Load | Total power | Steady-state temperature |
|---|---|---|
| Base only | 5 W | 7.5 C |
| + compression | 15 W | 22.5 C |
| + downlink | 20 W | 30 C |
| + inference | 25 W | 37.5 C |
| + compression + downlink | 30 W | 45 C |
| + inference wake | 35 W | 52.5 C (only lasts 2 ticks) |
| **+ inference + downlink** | **40 W** | **60 C, above the 50 C throttle limit** |

- **Throttle limit 50 C.** At or above it, the processing queue stalls and the accelerator parks. The chip then cools and compute resumes, so it self-regulates around the limit.
- **Time to throttle** under inference + downlink (computed): about **8 s** if inference is already running, about **16 s** from an idle start.
- **Only inference plus simultaneous downlink overheats the chip.** Every other combination stays below 50 C at default settings. Note the interaction: a pass is exactly when a controller wants to downlink, and running inference at the same time forces throttling. Each throttle event also parks the accelerator, so resuming costs another 2-tick wake at 30 W.
- **Why not real radiative cooling?** In space, a chip sheds heat by radiation, `Q = eps * sigma * A * (T^4 - T_env^4)`, which is non-linear. The linear model is a first-order approximation around the operating point, and `thermal_ambient_c` stands in for the bus/sink temperature. It captures the qualitative behaviour (temperature rises with load and relaxes when idle) with two easily explained coefficients. Shifting `thermal_ambient_c` is a Phase 9 stress scenario.
- All electrical power is treated as heat at the chip, which is a conservative simplification.

---

## 7. Storage and memory

| Resource | Capacity | Role |
|---|---|---|
| MMU (mass memory) | 32,000 MB | Non-volatile storage for payloads waiting to be processed or sent, **including payloads locked in the processing queue** |
| RAM | 4,000 MB | Working memory, holds a working copy of the payload for the **active** job only |

- **Queued payloads stay in MMU accounting.** When a `process` action is accepted, the payload leaves the `mmu_payloads` list (so it can no longer be downlinked or dropped) but its bytes stay in `mmu_used_mb` until the job completes. Completion swaps the footprint from the original size to the output size, which can only shrink it. The invariant, stated in the `Satellite` docstring and checked in `sanity_check.py`, is:

  ```
  mmu_used_mb == sum(size of payloads in mmu_payloads) + sum(size of payloads in processing_queue)
  ```

  Two consequences: enqueueing does not free space, so a policy cannot avoid involuntary drops by parking payloads in the queue; and `mmu_used_mb` can never exceed capacity.
- **Lazy RAM loading.** A queued job loads into RAM only when it becomes the active job. Only the head job is ever resident, and a payload larger than RAM is rejected at enqueue, so the stall-and-retry branch for a full RAM cannot trigger in the current design. It remains as a guard in case the design or config changes.
- **RAM is never the constraint at default settings.** The largest payload is 300 MB against 4,000 MB. `peak_ram_mb` will show about 7.5% at most. The `size > ram_capacity` rejection exists to prevent deadlock if someone changes the config.
- **MMU is the constraint.** Inflow is about 4.5 MB/s (Section 9). If nothing is sent or dropped, the MMU fills after about **7,160 s (1.3 orbits)**. After that, every new payload is dropped on arrival (`involuntary_drops`). This is the pressure that forces a controller to make room by processing or dropping. Processing makes room only when a job *completes* (about 70% of the payload for compression, about 99.9% for inference), because the source bytes are held until the output exists.

### 7.1 Single-event upsets (SEU)

Radiation can flip bits in memory. Each tick has probability `1e-5` of an SEU, i.e. one event per ~100,000 s: about **0.16 events per 3-orbit episode**, or about 0.9 per day. That is plausible in order of magnitude for commercial (COTS) memory in LEO, but cite a source in the paper before calling it calibrated.

Effect: RAM is wiped, the accelerator resets to `sleep`, and the whole processing queue returns to the `mmu_payloads` list at its original size (its bytes never left MMU accounting), so **in-progress work is lost but stored data survives**. This assumes the MMU is protected (for example by ECC or radiation-tolerant flash) and only working memory is vulnerable. At the default rate, SEUs are nearly absent from 3-orbit runs. They matter for the Phase 9 stress test with elevated `seu_probability`.

---

## 8. Communications

- **Ground-station pass.** One pass per orbit, starting at a random orbit time in **[1000, 3000] s** and lasting **120 to 180 s**. Downlink is only valid during the pass. The next orbit's window is pre-rolled (`next_gs_*`) so `time_to_next_gs` is correct from the first observation and the agent can plan across orbit boundaries.
- **Bandwidth.** 20 Mbps = **2.5 MB/s**, shared by all downlink actions within a tick. That gives about **300 to 450 MB per pass**, roughly 375 MB on average. Over three orbits, the heuristic run in `sanity_check.py` used 1,077.5 of 1,085 MB, so passes are saturated.
- **Radio power.** A flat **15 W** for every tick in which any downlink executed, independent of how many MB moved. That is about 2.2 kJ per pass, or **6 J per MB at full utilisation**.
- **Partial downlinks.** A payload larger than the remaining tick bandwidth is sent in pieces. Its `size_mb` shrinks, and **utility is credited only when the last byte is sent**, at the value it has *at that moment*. A half-sent payload keeps decaying.
- **Simplifications.** There is no link budget, elevation-dependent rate, weather fade, or antenna pointing. Bandwidth is constant during a pass, and every orbit has a pass. Real single-station LEO passes are less frequent, so this is deliberately optimistic to keep the scheduling problem focused on *what* to send.

---

## 9. Data generation, value and the resulting decision problem

### 9.1 Payloads

A payload arrives every 15 s (360 per orbit, **1,080 per 3-orbit episode**).

| | Optical (70%) | SAR (30%) |
|---|---|---|
| Size | 5 to 15 MB (mean 10) | 100 to 300 MB (mean 200) |
| Base value | U(10, 100) x (1 - cloud_cover), mean 27.5 | U(10, 100), mean 55 |
| Why | Cameras are cheap in data, but clouds block the view | Radar is an active sensor and sees through cloud, but produces large products |

`cloud_cover` is drawn uniformly per payload and scales optical value. Because `current_value()` already includes the cloud effect, an RL agent that observes value implicitly observes cloud quality; it does not need `cloud_cover` as a separate input.

**Value decay:** `value(t) = base_value * exp(-lambda * age)` with `lambda` in `[1e-4, 1e-3]` per second. That gives half-lives from about **693 s (11.5 min)** to **6,931 s (1.3 orbits)**, and after one full orbit (5,400 s) a payload retains between **0.5% and 58%** of its value. This models time-critical Earth observation (ship tracking, disaster response), where late data is worth less, and it is the reason "store for later" has a cost.

### 9.2 Scale mismatch: the core of the problem

| Quantity (default config) | Value |
|---|---|
| Mean payload size | 67 MB (SAR is ~90% of the bytes, optical ~70% of the count) |
| Data generated per orbit | about **24 GB** (72 GB per episode) |
| MMU capacity | 32 GB |
| Downlink capacity per pass | about **375 MB**, roughly **1.6%** of one orbit's raw volume |
| Mean generated value per payload | 35.75, i.e. about 38.6k per episode |

The options for a typical payload:

| Payload | Raw | Compressed | Inferred |
|---|---|---|---|
| Optical: 10 MB, value 27.5 | 27.5 for 10 MB | 24.8 for 3 MB (20 J) | 13.8 for 0.01 MB (100-160 J) |
| SAR: 200 MB, value 55 | 55 for 200 MB | 49.5 for 60 MB (20 J) | 27.5 for 0.2 MB (100-160 J) |

Even compressed, an orbit's data (about 7 GB) is far over the pass budget. Inference outputs for a whole orbit total about 24 MB, which *fits*, but at half value. The decision therefore looks like a **knapsack under a bandwidth budget**: infer most payloads, and spend the rest of each pass on upgrading the most valuable ones to compression. The rest of the budget is a **time-varying trade-off** with decay, storage pressure and energy timing. This is a hypothesis about the structure of good policies, not a measured result.

**Ceiling on decision quality *(estimate)*.** Delivered value is `(value ratio) x (decay while waiting)`. With one pass per orbit, typical waits are 1,350 to 2,700 s, which leaves about 29% to 51% of value on average. Together with the 0.5 inference ratio, expect decision quality far below 1. Values of roughly 0.1 to 0.2 for good policies would not indicate a bug. Compare policies against each other, and against a hindsight upper bound if you build one, rather than against 1.0.

---

## 10. Metrics: how they map to raw counters

All metrics come from counters on `Satellite`, not from the RL reward, so any policy (heuristic, RL, ablated) is scored identically.

| Problem 1 criterion | Definition | Counters |
|---|---|---|
| Decision quality | `downlinked_utility / total_generated_value_snapshot` | value at delivery (decayed and degraded) over raw generated `base_value` |
| Completed-task rate | `payloads_downlinked / payloads_generated` | counts delivered payloads |
| Energy | `cumulative_energy_j` | **marginal** compute + comm energy, **excluding the 5 W base load** (constant across policies, so excluding it makes differences visible) |
| Latency | creation to full delivery, in seconds | `cumulative_latency / payloads_downlinked`, plus a variant including ages from `queued_ages()` |
| Resource utilisation | mean occupancy of MMU and RAM, bandwidth used / available, throttle % | `cumulative_*_usage_mb`, `bandwidth_used_mb`, `throttle_ticks` |

Extra counters (`peak_*`, `dropped_value`, `seu_events`, `safe_mode_events`, drops) exist for analysis and cannot be reconstructed after a run. Energy is counted *after* the brownout zeroing, so a failed tick does not count energy that was never spent.

**Reading storage metrics.** `mmu_usage_mb` (and so `cumulative_mmu_usage_mb` and `peak_mmu_mb`) includes the bytes of payloads held in the processing queue. The `mmu_files` telemetry field counts only payloads still listed for downlink or drop, so the number of stored payloads is `mmu_files + queue_length`. `queued_ages()` already covers both groups.

---

## 11. Which parameters are grounded and which are assumed

| Parameter group | Basis | Confidence |
|---|---|---|
| Orbit period, eclipse fraction | Typical LEO | Good |
| Solar power, battery size | Plausible small-satellite class | Reasonable |
| 30% state-of-charge floor | LEO battery-life practice | Reasonable |
| Comm power 15 W, 20 Mbps | Plausible X-band smallsat | Reasonable |
| Compute power 10/20/30 W | Edge-accelerator class | Assumed |
| SEU rate | COTS memory in LEO, order of magnitude | Order-of-magnitude |
| **Compression/inference size and value ratios** | **Chosen to create a trade-off** | **Assumed, needs sensitivity analysis** |
| **Value range, decay rates** | **Chosen to make timing matter** | **Assumed** |
| Thermal coefficients | Lumped model, tuned for behaviour | Assumed |
| `max_queue_length` = 4 | Chosen to bound how much data a policy can lock in the queue | Assumed, include in sensitivity analysis |

Say this openly in the paper: the study shows which *policies* handle the trade-offs well, not that the numbers match a particular spacecraft.

---

## 12. Known simplifications and caveats

Worth knowing before trusting RL results, and worth mentioning in a limitations section.

1. **Queued payloads are locked, and the agent sees little of the queue.** Once a `process` action is accepted, the payload cannot be downlinked, dropped or re-processed until its job completes, and there is no action to cancel a job. Only an SEU, safe mode or a brownout clears the queue. If the chip throttles, the queue stalls and its payloads wait. The lock is bounded by `max_queue_length` (default 4); a `process` action beyond that returns a `Queue full` feedback error. Telemetry exposes `queue_length` and the head job's `processing_progress` / `processing_required`, but not the IDs, modes or values of the waiting jobs, so a policy must track those itself.
2. **Battery clamp.** The battery can never drop below the floor, which implicitly assumes the base load is powered from a protected reserve. There are no charging losses, temperature effects or charge-rate limits.
3. **Linear thermal model with a fixed ambient.** The ambient is not coupled to sun or eclipse, and the model has one thermal node.
4. **One GS pass per orbit** with constant bandwidth, no link budget, and no weather. `time_to_next_gs` reads 0 during a pass, so the *remaining* pass time is not observable from telemetry.
5. **Deterministic processing.** Inference and compression always succeed and always give fixed ratios. There is no model accuracy, false-positive or content dependence.
6. **Serial compute only.** One job at a time, with no CPU/GPU load metric.
7. **Partial downlinks mutate `size_mb`.** The original payload size is lost, so later value-density or data-volume metrics need an `original_size_mb` field. A partly downlinked payload also remains eligible for `process`; the job then compresses or infers only the remaining bytes, which has no physical meaning. Consider rejecting `process` on a payload whose size has been reduced.
8. **GS sentinel.** `_randomize_gs_pass` treats `next_gs_start == 0` as "first call". That is safe while `gs_start_min >= 1`, but a stress scenario with `gs_start_min = 0` could re-trigger initialisation. Use an explicit flag if you change that range.
9. **Priority is only value.** There are no explicit priority classes or deadlines beyond exponential decay.
10. **A warm accelerator is free and sticky.** The `active` state draws no idle power, and it is parked only when step 5 runs with an empty queue or a throttled chip while the state is `active`. Compression jobs do not touch the state, so once the accelerator is warm, a `[compress, infer]` sequence does not pay the 2-tick wake, and an inference job queued on the first tick after another job finishes stays warm. A policy that re-queues promptly can therefore avoid the 60 J cold-start cost more often than the per-job arithmetic in Section 5.1 suggests. A `waking` accelerator is never parked: its countdown simply freezes while the chip is throttled. SEU, safe mode and brownout still reset the state to `sleep`.
11. **A brownout tick still delivers its downlinks.** Actions run in step 4 and the power check runs in step 6. If a tick browns out, the radio power is zeroed and safe mode begins, but any downlink already executed that tick keeps its bandwidth use and credited utility, even though the energy for it was never spent. The effect is at most one tick of bandwidth (2.5 MB) per brownout, so it is small, but it is a free delivery.

### 12.1 Resolved since the previous revision

- **Uncounted, unbounded queue.** Queued payloads used to leave MMU accounting at enqueue and the queue had no length limit, so a policy could enqueue many payloads to free MMU space and avoid involuntary drops. Queued payloads now stay in `mmu_used_mb` until their job completes, and the queue is capped by `max_queue_length`.
- **Transient MMU over-capacity.** Returning payloads after an SEU, safe mode or a completion used to re-add their size without a capacity check, so `mmu_used <= capacity` could fail by up to one payload. Recovery no longer touches MMU accounting, and completion can only shrink a footprint, so this cannot happen. The storage invariant holds up to floating-point rounding, so checks should use a small tolerance rather than exact equality.

---

## 13. Changes in this version

### 13.1 Since the previous revision (queue accounting)

- **Queued payloads stay in MMU accounting until the job completes.** Enqueueing removes the payload from `mmu_payloads` but leaves `mmu_used_mb` unchanged. Completion swaps the original size for the output size. `_recover_processing_queue` (SEU, safe mode, brownout) returns payloads to the list without touching MMU accounting, so only the RAM working copy and the job's progress are lost. The storage invariant is stated in the `Satellite` docstring (Section 7).
- **New parameter `max_queue_length`** (default 4, validated to be at least 1). A `process` action beyond it returns a `Queue full` feedback error.
- **Comparability.** No random draw depends on the agent's actions and none was added, so payload sizes, arrival times, GS windows and SEU events are identical to the previous revision for the same seed. Any result from a policy that used the queue to free MMU space, or that held more than four jobs, is out of date: rerun those baselines, and expect changes in `involuntary_drops`, `dropped_value` and the MMU occupancy metrics.
- **Section 12 caveats 1 and 2 of the previous revision are resolved** (Section 12.1). Sections 4.3, 5.1, 5.2, 7, 10 and 11 were updated to match. Section 12 items 10 and 11 (accelerator warmth, brownout-tick downlinks) document existing behaviour found while checking the text against `step()`; the code did not change for them.

### 13.2 Earlier changes (still apply)

- **Cloud cover affects optical value** (`base_value *= 1 - cloud_cover`). SAR is unaffected, which is physically motivated. The random-number consumption order is unchanged. **Only optical values changed**, so any baseline numbers computed before that change are out of date.
- **`peak_temp_c` initialises to `thermal_ambient_c`**, so stress scenarios with a shifted ambient report the right peak.
- Value-ratio degradation, GS pre-roll and lookahead, the metric counters, energy counted after brownout, and the `queued_ages()` helper.