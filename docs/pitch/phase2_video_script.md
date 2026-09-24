# ASTRA — Two-Minute Video Pitch

**Target submission date:** October 2, 2026 (team-provided date)  
**Estimated spoken length:** about 230 words; rehearse with a timer and keep the finished video under two minutes.

| Time | Spoken script | Suggested visual |
|---|---|---|
| 0:00–0:20 | An Earth-observation satellite collects data every fifteen seconds, but contacts a ground station only during brief passes. Its battery, memory, and thermal headroom are limited. So each payload raises the same question: process it, queue it, transmit it raw, or drop it? | Satellite collects frames; show a short ground-contact window against a 90-minute orbit. Put the four choices on screen. |
| 0:20–0:43 | Our solution is **ASTRA: Adaptive Satellite Task and Resource Allocator**. It addresses IASTAM’s “Process or Transmit?” challenge. The prototype simulates orbit, battery, storage, communication, temperature, and the processing queue, then weighs payload value against current resources and ground contact. | Reveal the simulator view, then a simple flow: payload → ASTRA → compute, buffer, downlink, or drop. |
| 0:43–1:08 | Today, a transparent rule-based policy is our working baseline. It transmits during ground contact, schedules compression or inference when battery and thermal conditions allow, and keeps pending data in memory. In the simulator, compression reduces a payload to thirty percent of its size; inference reduces it to 0.1 percent, with a modeled utility trade-off. | Animate one raw payload through compression and inference. Label both reductions as simulator assumptions. |
| 1:08–1:38 | We evaluated that baseline across five fixed seeds, with four simulated orbits per run. It delivered about 2.83 percent of generated value and completed about 1.53 percent of payloads. Mean modeled energy use was 291 kilojoules; completed deliveries took about 654 seconds on average. These are simulation measurements—not flight data or proof that our policy beats alternatives. | Show the results table and the battery/temperature trajectory. Keep “five seeds” and “simulation” visible. |
| 1:38–2:00 | The results expose the bottleneck and give us a reproducible baseline. Next, we will compare schedulers, test more operating conditions, and improve thermal safety. ASTRA aims to help satellites send the most useful information they can with the resources they have. | End on “Measure → Compare → Improve,” then the ASTRA name and team name. |

## Recording notes

- Keep the total runtime at or below two minutes; trim pauses before cutting the caveat that results are simulated.
- The simulator’s 50°C threshold throttles compute but does not guarantee a hard temperature cap. Do not describe it as flight-safe thermal control.
- The current measured policy is a rule-based baseline. The RL environment exists, but no trained-policy result is reported. Lyapunov and MILP comparisons remain future work.
- Confirm team name, affiliation, and presenter names before adding them to the closing frame.
