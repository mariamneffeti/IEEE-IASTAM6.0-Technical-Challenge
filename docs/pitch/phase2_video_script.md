# ASTRA — Two-Minute Video Pitch

**Team-stated video target:** October 2, 2026. The repository's IASTAM challenge calendar lists the Phase 2 paper and video deadline as September 26, 2026. Confirm that October 2 is an approved extension or a separate team deadline before relying on it.

**Estimated spoken length:** 218 words. Rehearse with a timer and keep the finished video under two minutes.

| Time | Spoken script | Suggested visual |
|---|---|---|
| 0:00–0:22 | An Earth-observation satellite generates a payload every fifteen seconds, but ground-station contact comes in short passes. Battery, storage, and thermal limits mean it cannot simply keep everything and send it later. For each payload, should it process, queue, transmit raw, or discard? | Show a 90-minute orbit, short contact window, and the four choices. |
| 0:22–0:44 | We built ASTRA: Adaptive Satellite Task and Resource Allocator. Our one-second simulator models orbit, battery, storage, communication, temperature, and processing queues. We compare four policies: transmit-all, greedy-edge processing, a threshold heuristic, and a learned PPO agent. | Show the simulator, then payload flowing to compute, buffer, downlink, or discard. |
| 0:44–1:06 | We ran five paired scenarios, each covering four simulated orbits. The heuristic delivered the highest utility ratio, 2.86 percent. Greedy-edge completed the most payloads, 5.17 percent, but delivered a lower utility ratio. | Reveal the comparison plot; highlight decision quality and completion rate. |
| 1:06–1:34 | Our first PPO checkpoint completed no tasks. Its lower energy use is an inactivity result, not an efficiency gain. That tells us the learning setup needs more training and reward diagnostics. These are early simulator results, not flight measurements, and the heuristic's 2.86 percent utility ratio shows there is significant room to improve. | Show PPO’s zero completion and call out “one training seed; exploratory.” |
| 1:34–2:00 | The simulator also shows why safety needs careful treatment: its 50-degree compute throttle is not a hard temperature cap, and one trace exceeded it. Next we will improve thermal validation, train across multiple seeds, and add Lyapunov and oracle comparisons. ASTRA gives us a reproducible way to measure those decisions. | Show battery/temperature trace, then “Measure → Compare → Improve” and ASTRA title. |

## Recording notes

- Keep runtime at or below two minutes; preserve the caveat that results are synthetic.
- Describe the PPO result as an unsuccessful initial run; do not claim that it establishes RL as inferior.
- The simulator's 50°C threshold throttles compute but is not a hard temperature limit.
- Confirm the official video deadline against the registered-team submission instructions; this file records the team's October 2 target while the repository challenge calendar says September 26.
- Confirm the registered team name and affiliation before placing them in the closing frame.
