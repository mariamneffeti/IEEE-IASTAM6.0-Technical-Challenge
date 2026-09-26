# ASTRA — Two-Minute Video Pitch

**Submission timing is unresolved:** The repository calendar lists the Phase 2 paper and video deadline as September 26, 2026, while the team's stated video target is October 2. I could not verify an official extension in the available organizer sources. Confirm the registered team's current submission instructions before relying on October 2.

**Estimated spoken length:** 212 words. Rehearse with a timer and keep the finished video under two minutes.

| Time | Spoken script | Suggested visual |
|---|---|---|
| 0:00–0:22 | In our simulation, an Earth-observation payload arrives every fifteen seconds, but ground-station contact comes in short passes. Battery, storage, and thermal limits mean the satellite cannot simply keep everything and send it later. For each payload, should it process, queue, transmit raw, or discard? | Show a 90-minute orbit, short contact window, and the four choices. |
| 0:22–0:44 | We built ASTRA: Adaptive Satellite Task and Resource Allocator. Our one-second simulator models orbit, battery, storage, communication, temperature, and processing queues. We compare four policies: transmit-all, greedy-edge processing, a threshold heuristic, and a learned PPO agent. | Show the simulator, then payload flowing to compute, buffer, downlink, or discard. |
| 0:44–1:06 | We ran five paired scenarios, each covering four simulated orbits. The heuristic delivered the highest utility ratio, 2.86 percent. Greedy-edge completed the most payloads, 5.17 percent, but delivered a lower utility ratio. | Reveal the comparison plot; highlight decision quality and completion rate. |
| 1:06–1:34 | Our first PPO checkpoint completed no tasks. It used less energy than the processing-heavy policies but more than transmit-all, so its lower draw reflects inactivity, not efficiency. The result guides more training and reward diagnostics. These are simulator results, not flight measurements; the heuristic's 2.86 percent utility ratio leaves clear room to improve. | Show PPO’s zero completion and call out “one training seed; exploratory.” |
| 1:34–2:00 | The simulator's 50-degree compute throttle is not a hard cap; one trace reached 52.48 degrees. Next, we will validate thermal behavior, train PPO across seeds, and add Lyapunov and oracle comparisons. ASTRA gives us a reproducible way to evaluate these choices. | Show battery/temperature trace, then “Measure → Compare → Improve” and ASTRA title. |

## Recording notes

- Keep runtime at or below two minutes; preserve the caveat that results are synthetic.
- Describe the PPO result as an unsuccessful initial run; do not claim that it establishes RL as inferior.
- The simulator's 50°C threshold throttles compute but is not a hard temperature limit.
- Confirm the registered team's current deadline: the repository calendar says September 26, while the team's stated target is October 2; no extension is verified here.
- Use the confirmed team identity in the closing frame: Charmoula wMa9rou4; Mariam Neffeti (INSAT) and Mohamed Habib Abid (ISI El Manar).
